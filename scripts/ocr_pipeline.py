"""
ktunDepo Agent — OCR Pipeline
PDF tarama ve Markdown formatlaması.

OCR Araçları Öncelik Sırası:
1. Docling (IBM) - Ücretsiz, lokal, tablo+formül desteği
2. Tesseract - Yedek, Türkçe dil paketi ile
3. Mistral OCR API - Ücretli, en yüksek kalite
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

# Lazy imports
try:
    from docling.document_converter import DocumentConverter

    HAS_DOCLING = True
except ImportError:
    HAS_DOCLING = False

try:
    import pytesseract
    from PIL import Image
    import pdf2image

    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


@dataclass
class OCRResult:
    """OCR işlem sonucu."""

    success: bool
    text: str = ""
    markdown: str = ""
    engine_used: str = ""
    page_count: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class OCRPipeline:
    """
    PDF OCR ve yapısal parse işlemleri.

    Öncelik sırası:
    1. Docling - Yapısal parse, tablo/formül desteği
    2. Tesseract - Basit OCR fallback
    """

    DEFAULT_CONFIG = {
        "engine": "docling",
        "language": "tr",
        "tesseract_lang": "tur",
        "max_pages": 100,
        "dpi": 300,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        OCRPipeline başlat.

        Args:
            config: Yapılandırma dict'i
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self._docling_converter = None

    def _get_docling_converter(self):
        """Docling converter lazy init."""
        if self._docling_converter is None and HAS_DOCLING:
            self._docling_converter = DocumentConverter()
        return self._docling_converter

    def needs_ocr(self, pdf_path: str) -> bool:
        """
        PDF'in OCR'a ihtiyacı olup olmadığını belirle.

        Args:
            pdf_path: PDF dosya yolu

        Returns:
            True eğer OCR gerekli
        """
        try:
            # pypdf ile metin katmanı kontrolü
            from pypdf import PdfReader

            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                total_chars = 0
                pages_checked = min(3, len(reader.pages))

                for i in range(pages_checked):
                    text = reader.pages[i].extract_text() or ""
                    total_chars += len(text)

                avg_chars = total_chars / pages_checked if pages_checked > 0 else 0

                # Sayfa başına 100 karakterden az → OCR gerekli
                return avg_chars < 100

        except Exception:
            # Hata durumunda OCR gerekli varsay
            return True

    def process_pdf(self, pdf_path: str) -> OCRResult:
        """
        PDF'i işle ve metin çıkar.

        Args:
            pdf_path: PDF dosya yolu

        Returns:
            OCRResult objesi
        """
        path = Path(pdf_path)
        if not path.exists():
            return OCRResult(success=False, error=f"Dosya bulunamadı: {pdf_path}")

        # Engine seçimi
        engine = self.config["engine"]

        if engine == "docling" and HAS_DOCLING:
            return self._process_with_docling(pdf_path)
        elif HAS_TESSERACT:
            return self._process_with_tesseract(pdf_path)
        else:
            return OCRResult(
                success=False, error="Kullanılabilir OCR engine bulunamadı"
            )

    def _process_with_docling(self, pdf_path: str) -> OCRResult:
        """Docling ile PDF işle."""
        try:
            converter = self._get_docling_converter()
            if converter is None:
                return OCRResult(success=False, error="Docling başlatılamadı")

            result = converter.convert(pdf_path)

            # Markdown çıktısı al
            markdown = result.document.export_to_markdown()

            # Düz metin — markdown'dan türet (Docling API versiyonlarına göre değişir)
            text = markdown

            # Sayfa sayısı ve metadata — API versiyonuna bağlı, güvenli şekilde al
            try:
                page_count = result.document.num_pages
            except (AttributeError, TypeError):
                page_count = markdown.count("<!-- page") or None

            try:
                doc_title = result.document.name
            except AttributeError:
                doc_title = None

            try:
                has_tables = "| " in markdown or "|-" in markdown
            except Exception:
                has_tables = False

            return OCRResult(
                success=True,
                text=text,
                markdown=markdown,
                engine_used="docling",
                page_count=page_count,
                metadata={
                    "title": doc_title,
                    "has_tables": has_tables,
                },
            )

        except Exception as e:
            return OCRResult(
                success=False, error=f"Docling hatası: {str(e)}", engine_used="docling"
            )

    def _process_with_tesseract(self, pdf_path: str) -> OCRResult:
        """Tesseract ile PDF işle."""
        try:
            # PDF'i görüntülere dönüştür
            images = pdf2image.convert_from_path(
                pdf_path, dpi=self.config["dpi"], last_page=self.config["max_pages"]
            )

            text_parts = []
            for i, image in enumerate(images):
                page_text = pytesseract.image_to_string(
                    image, lang=self.config["tesseract_lang"]
                )
                text_parts.append(f"--- Sayfa {i + 1} ---\n{page_text}")

            full_text = "\n\n".join(text_parts)

            return OCRResult(
                success=True,
                text=full_text,
                markdown=full_text,  # Tesseract yapısal parse yapmaz
                engine_used="tesseract",
                page_count=len(images),
            )

        except Exception as e:
            return OCRResult(
                success=False,
                error=f"Tesseract hatası: {str(e)}",
                engine_used="tesseract",
            )

    def extract_text_from_pages(
        self, pdf_path: str, start_page: int = 0, end_page: int = 3
    ) -> str:
        """
        Belirli sayfalardan metin çıkar (duplicate tespiti için).

        Args:
            pdf_path: PDF dosya yolu
            start_page: Başlangıç sayfası (0-indexed)
            end_page: Bitiş sayfası (exclusive)

        Returns:
            Çıkarılan metin
        """
        try:
            from pypdf import PdfReader

            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                text_parts = []

                for i in range(start_page, min(end_page, len(reader.pages))):
                    page_text = reader.pages[i].extract_text() or ""
                    text_parts.append(page_text)

                return "\n".join(text_parts)

        except Exception:
            return ""


class MarkdownFormatter:
    """
    OCR çıktısını temiz Markdown'a dönüştür.
    LLM kullanarak formatlama yapar.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "anthropic/claude-3.5-sonnet-20241022",
    ):
        """
        MarkdownFormatter başlat.

        Args:
            api_key: OpenRouter API key
            model: Kullanılacak model
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model
        self._client = None

    def _get_client(self):
        """OpenAI client lazy init (via OpenRouter)."""
        if self._client is None and self.api_key:
            try:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=self.api_key, base_url="https://openrouter.ai/api/v1"
                )
            except ImportError:
                pass
        return self._client

    def format_text(
        self,
        raw_text: str,
        course_name: Optional[str] = None,
        material_type: Optional[str] = None,
    ) -> Tuple[str, int]:
        """
        Ham metni Markdown'a formatla.

        Args:
            raw_text: OCR'dan gelen ham metin
            course_name: Ders adı (context için)
            material_type: Materyal türü

        Returns:
            (formatted_markdown, tokens_used) tuple
        """
        client = self._get_client()
        if client is None:
            # LLM yoksa basit temizlik
            return self._simple_cleanup(raw_text), 0

        # Prompt yükle
        prompt_path = Path("agent/prompts/markdown_format.md")
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        else:
            system_prompt = "Ham OCR metnini temiz Markdown'a dönüştür."

        # Context ekle
        user_message = ""
        if course_name:
            user_message += f"Ders: {course_name}\n"
        if material_type:
            user_message += f"Materyal türü: {material_type}\n"
        user_message += f"\nHam metin:\n{raw_text}"

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=8096,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )

            formatted = response.choices[0].message.content
            tokens = response.usage.prompt_tokens + response.usage.completion_tokens

            return formatted, tokens

        except Exception as e:
            return self._simple_cleanup(raw_text), 0

    def _simple_cleanup(self, text: str) -> str:
        """LLM olmadan basit metin temizliği."""
        lines = text.split("\n")
        cleaned = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Sayfa numarası gibi görünen satırları atla
            if line.isdigit() and len(line) < 4:
                continue
            cleaned.append(line)

        return "\n".join(cleaned)


# Singleton instances
_ocr_pipeline: Optional[OCRPipeline] = None
_markdown_formatter: Optional[MarkdownFormatter] = None


def get_ocr_pipeline(config: Optional[Dict[str, Any]] = None) -> OCRPipeline:
    """Global OCRPipeline instance."""
    global _ocr_pipeline
    if _ocr_pipeline is None:
        _ocr_pipeline = OCRPipeline(config)
    return _ocr_pipeline


def get_markdown_formatter() -> MarkdownFormatter:
    """Global MarkdownFormatter instance."""
    global _markdown_formatter
    if _markdown_formatter is None:
        _markdown_formatter = MarkdownFormatter()
    return _markdown_formatter
