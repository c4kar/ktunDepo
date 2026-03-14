"""
ktunDepo Intake Agent — Docling Gateway

Amaç:
- PDF dosyalarından Docling ile metin/yapı çıkarmak
- Büyük taranmış PDF'leri intake aşamasında optimize etmek
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agent.intake.file_scanner import ScanResult

try:
    from docling.document_converter import DocumentConverter

    HAS_DOCLING = True
except ImportError:
    HAS_DOCLING = False

try:
    from pdf2image import convert_from_path
    from PIL import Image

    HAS_PDF_TO_IMAGE = True
except ImportError:
    HAS_PDF_TO_IMAGE = False


@dataclass
class DoclingExtractionResult:
    success: bool
    text: str = ""
    markdown: str = ""
    extracted_chars: int = 0
    quality_score: int = 0
    reason: str = ""


@dataclass
class OptimizationResult:
    optimized: bool
    old_size_mb: float = 0.0
    new_size_mb: float = 0.0
    saved_percent: float = 0.0
    reason: str = ""


class DoclingGateway:
    """Docling extraction + intake PDF optimization helper."""

    def __init__(
        self,
        min_extracted_chars: int = 180,
        optimize_pdf_over_mb: float = 20.0,
        optimize_min_saving_percent: float = 20.0,
        optimize_max_pages: int = 120,
        optimize_dpi: int = 150,
        optimize_jpeg_quality: int = 60,
    ):
        self.min_extracted_chars = min_extracted_chars
        self.optimize_pdf_over_mb = optimize_pdf_over_mb
        self.optimize_min_saving_percent = optimize_min_saving_percent
        self.optimize_max_pages = optimize_max_pages
        self.optimize_dpi = optimize_dpi
        self.optimize_jpeg_quality = optimize_jpeg_quality
        self._converter: Optional[DocumentConverter] = None

    def _get_converter(self) -> Optional[DocumentConverter]:
        if not HAS_DOCLING:
            return None
        if self._converter is None:
            self._converter = DocumentConverter()
        return self._converter

    def extract_pdf(self, file_path: str) -> DoclingExtractionResult:
        """Run Docling extraction for a PDF file."""
        converter = self._get_converter()
        if converter is None:
            return DoclingExtractionResult(False, reason="docling unavailable")

        try:
            result = converter.convert(file_path)
            markdown = result.document.export_to_markdown() or ""
            text = markdown
            extracted_chars = len(text.strip())

            quality_score = self._score_extraction_quality(text)
            if extracted_chars < self.min_extracted_chars:
                return DoclingExtractionResult(
                    success=False,
                    text=text,
                    markdown=markdown,
                    extracted_chars=extracted_chars,
                    quality_score=quality_score,
                    reason=f"insufficient extracted chars: {extracted_chars}",
                )

            return DoclingExtractionResult(
                success=True,
                text=text,
                markdown=markdown,
                extracted_chars=extracted_chars,
                quality_score=quality_score,
                reason="ok",
            )
        except Exception as e:
            return DoclingExtractionResult(False, reason=f"docling error: {e}")

    def maybe_optimize_scanned_pdf(
        self, file_path: str, scan: ScanResult
    ) -> OptimizationResult:
        """
        Büyük taranmış PDF dosyalarını inplace optimize eder.

        Notlar:
        - Sadece .pdf + metin katmanı yok + büyük dosya durumunda çalışır.
        - Anlamlı kazanç yoksa (varsayılan < %20) orijinal dosyayı korur.
        """
        path = Path(file_path)
        if not path.exists():
            return OptimizationResult(False, reason="file missing")

        if scan.extension.lower() != ".pdf":
            return OptimizationResult(False, reason="not pdf")

        if scan.has_text_layer:
            return OptimizationResult(False, reason="text-layer pdf; skip")

        old_size_mb = scan.size_mb
        if old_size_mb < self.optimize_pdf_over_mb:
            return OptimizationResult(
                False, old_size_mb=old_size_mb, reason="below threshold"
            )

        if not HAS_PDF_TO_IMAGE:
            return OptimizationResult(
                False, old_size_mb=old_size_mb, reason="pdf2image/Pillow unavailable"
            )

        page_count = scan.page_count or 1
        if page_count > self.optimize_max_pages:
            return OptimizationResult(
                False,
                old_size_mb=old_size_mb,
                reason=f"too many pages ({page_count})",
            )

        with tempfile.TemporaryDirectory(prefix="ktundepo_pdfopt_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            optimized_pdf = tmp_path / f"{path.stem}.optimized.pdf"

            all_images = []
            try:
                # Bellek kullanımını sınırlamak için küçük chunk'lar halinde çevir.
                chunk_size = 12
                start = 1
                while start <= page_count:
                    end = min(start + chunk_size - 1, page_count)
                    pages = convert_from_path(
                        str(path),
                        first_page=start,
                        last_page=end,
                        dpi=self.optimize_dpi,
                    )
                    for page in pages:
                        all_images.append(page.convert("RGB"))
                    start = end + 1

                if not all_images:
                    return OptimizationResult(
                        False, old_size_mb=old_size_mb, reason="no rendered pages"
                    )

                all_images[0].save(
                    optimized_pdf,
                    format="PDF",
                    save_all=True,
                    append_images=all_images[1:],
                    quality=self.optimize_jpeg_quality,
                    optimize=True,
                )
            except Exception as e:
                return OptimizationResult(
                    False, old_size_mb=old_size_mb, reason=f"optimize error: {e}"
                )

            if not optimized_pdf.exists() or optimized_pdf.stat().st_size == 0:
                return OptimizationResult(
                    False, old_size_mb=old_size_mb, reason="optimized file invalid"
                )

            new_size_mb = optimized_pdf.stat().st_size / (1024 * 1024)
            if old_size_mb <= 0:
                return OptimizationResult(
                    False, old_size_mb=old_size_mb, reason="invalid original size"
                )

            saved_percent = max(
                0.0, ((old_size_mb - new_size_mb) / old_size_mb) * 100.0
            )
            if saved_percent < self.optimize_min_saving_percent:
                return OptimizationResult(
                    False,
                    old_size_mb=old_size_mb,
                    new_size_mb=new_size_mb,
                    saved_percent=saved_percent,
                    reason="saving below threshold",
                )

            # Inplace replace
            os.replace(str(optimized_pdf), str(path))

            return OptimizationResult(
                True,
                old_size_mb=old_size_mb,
                new_size_mb=new_size_mb,
                saved_percent=saved_percent,
                reason="optimized",
            )

    def _score_extraction_quality(self, text: str) -> int:
        """Cheap extraction quality proxy (0-100)."""
        stripped = text.strip()
        if not stripped:
            return 0

        length = len(stripped)
        alpha = sum(ch.isalpha() for ch in stripped)
        digit = sum(ch.isdigit() for ch in stripped)
        space = sum(ch.isspace() for ch in stripped)
        printable_ratio = (alpha + digit + space) / max(1, length)

        score = 0
        if length >= 150:
            score += 35
        elif length >= 80:
            score += 20
        elif length >= 40:
            score += 10

        if printable_ratio >= 0.75:
            score += 35
        elif printable_ratio >= 0.55:
            score += 20
        elif printable_ratio >= 0.40:
            score += 10

        lines = stripped.count("\n") + 1
        if lines >= 8:
            score += 20
        elif lines >= 4:
            score += 10

        if any(ch in stripped for ch in "abcçdefgğhıijklmnoöprsştuüvyz"):
            score += 10

        return max(0, min(100, score))
