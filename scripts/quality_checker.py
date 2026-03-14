"""
ktunDepo Agent — Quality Checker
Materyal kalite eleme motoru — heuristik + LLM tabanlı değerlendirme.

Bu modül token tasarrufu için aşamalı filtreleme uygular:
1. Dosya analizi (0 token)
2. Heuristik kalite skoru (0 token)
3. Duplicate tespiti (vektör arama)
4. LLM değerlendirmesi (sadece gerekirse)
"""

import os
import mimetypes
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Any
from enum import Enum
from datetime import datetime

# PDF işleme için lazy import (kurulum sonrası çalışır)
try:
    from pypdf import PdfReader

    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import pdfplumber

    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


class QualityDecision(Enum):
    """Kalite değerlendirme kararları."""

    ACCEPTED = "accepted"  # Kabul edildi, depoya ekle
    REJECTED = "rejected"  # Reddedildi, sil
    DUPLICATE = "duplicate"  # Zaten mevcut
    SIMILAR_EXISTS = "similar"  # Benzer var, LLM'e sor
    NEEDS_LLM = "needs_llm"  # LLM değerlendirmesi gerekli
    NEEDS_OCR = "needs_ocr"  # OCR gerekli, sonra tekrar değerlendir


@dataclass
class FileMetadata:
    """Dosya metadata bilgileri."""

    path: str
    filename: str
    extension: str
    size_bytes: int
    size_kb: float
    size_mb: float
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    mime_type: Optional[str] = None


@dataclass
class PDFMetadata:
    """PDF-spesifik metadata."""

    page_count: int = 0
    total_chars: int = 0
    avg_chars_per_page: float = 0.0
    avg_words_per_page: float = 0.0
    has_images: bool = False
    has_tables: bool = False
    language_detected: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[str] = None
    is_scannable: bool = False  # OCR gerekli mi


@dataclass
class QualityResult:
    """Kalite değerlendirme sonucu."""

    decision: QualityDecision
    score: int = 50  # 0-100 arası
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    file_metadata: Optional[FileMetadata] = None
    pdf_metadata: Optional[PDFMetadata] = None
    suggested_path: Optional[str] = None
    processing_time_ms: float = 0


class QualityChecker:
    """
    Materyal kalite eleme motoru.

    Aşamalı filtreleme ile token tasarrufu sağlar:
    - Aşama 1: Dosya analizi (uzantı, boyut)
    - Aşama 2: PDF metadata analizi (sayfa sayısı, metin yoğunluğu)
    - Aşama 3: Heuristik skor hesaplama
    - Aşama 4: LLM değerlendirmesi (sadece gerekirse)
    """

    # Varsayılan eşik değerleri
    DEFAULT_CONFIG = {
        "reject_threshold": 30,
        "llm_threshold": 60,
        "min_file_size_kb": 50,
        "max_file_size_mb": 200,
        "min_pages": 2,
        "supported_extensions": [".pdf", ".pptx", ".docx", ".mp4", ".mkv"],
        "ocr_chars_threshold": 100,  # Sayfa başına bu karakterden az → OCR gerekli
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        QualityChecker başlat.

        Args:
            config: Yapılandırma dict'i (None ise varsayılan kullanılır)
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

    def check_file(self, file_path: str) -> QualityResult:
        """
        Dosyayı tüm aşamalardan geçir.

        Args:
            file_path: Kontrol edilecek dosya yolu

        Returns:
            QualityResult objesi
        """
        start_time = datetime.now()

        # Aşama 1: Dosya varlık ve temel kontroller
        file_meta = self._analyze_file(file_path)
        if file_meta is None:
            return QualityResult(
                decision=QualityDecision.REJECTED,
                score=0,
                reason="Dosya bulunamadı veya okunamadı",
            )

        # Uzantı kontrolü
        if file_meta.extension.lower() not in self.config["supported_extensions"]:
            return QualityResult(
                decision=QualityDecision.REJECTED,
                score=0,
                reason=f"Desteklenmeyen dosya formatı: {file_meta.extension}",
                file_metadata=file_meta,
            )

        # Boyut kontrolleri
        size_result = self._check_file_size(file_meta)
        if size_result is not None:
            size_result.file_metadata = file_meta
            return size_result

        # PDF için özel analiz
        pdf_meta = None
        if file_meta.extension.lower() == ".pdf":
            pdf_meta = self._analyze_pdf(file_path)

            # Sayfa sayısı kontrolü
            if pdf_meta.page_count < self.config["min_pages"]:
                return QualityResult(
                    decision=QualityDecision.REJECTED,
                    score=15,
                    reason=f"Yetersiz sayfa sayısı: {pdf_meta.page_count} sayfa",
                    file_metadata=file_meta,
                    pdf_metadata=pdf_meta,
                )

            # OCR gerekli mi?
            if pdf_meta.is_scannable:
                return QualityResult(
                    decision=QualityDecision.NEEDS_OCR,
                    score=50,
                    reason="Taranmış görüntü tespit edildi, OCR gerekli",
                    file_metadata=file_meta,
                    pdf_metadata=pdf_meta,
                )

        # Aşama 2: Heuristik skor hesapla
        score = self._calculate_heuristic_score(file_meta, pdf_meta)

        # Karar ver
        if score < self.config["reject_threshold"]:
            decision = QualityDecision.REJECTED
            reason = f"Kalite skoru çok düşük: {score}/100"
        elif score < self.config["llm_threshold"]:
            decision = QualityDecision.NEEDS_LLM
            reason = f"LLM değerlendirmesi gerekli (skor: {score}/100)"
        else:
            decision = QualityDecision.ACCEPTED
            reason = f"Heuristik değerlendirme ile kabul (skor: {score}/100)"

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds() * 1000

        return QualityResult(
            decision=decision,
            score=score,
            reason=reason,
            file_metadata=file_meta,
            pdf_metadata=pdf_meta,
            processing_time_ms=processing_time,
        )

    def _analyze_file(self, file_path: str) -> Optional[FileMetadata]:
        """Temel dosya metadata analizi."""
        path = Path(file_path)

        if not path.exists():
            return None

        try:
            stat = path.stat()
            size_bytes = stat.st_size

            return FileMetadata(
                path=str(path.absolute()),
                filename=path.name,
                extension=path.suffix,
                size_bytes=size_bytes,
                size_kb=size_bytes / 1024,
                size_mb=size_bytes / (1024 * 1024),
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                mime_type=mimetypes.guess_type(str(path))[0],
            )
        except (OSError, IOError):
            return None

    def _check_file_size(self, file_meta: FileMetadata) -> Optional[QualityResult]:
        """Dosya boyutu kontrolü."""
        # Minimum boyut
        if file_meta.size_kb < self.config["min_file_size_kb"]:
            return QualityResult(
                decision=QualityDecision.REJECTED,
                score=0,
                reason=f"Dosya çok küçük: {file_meta.size_kb:.1f}KB (min: {self.config['min_file_size_kb']}KB)",
            )

        # Maksimum boyut (video hariç)
        is_video = file_meta.extension.lower() in [".mp4", ".mkv"]
        max_size = 500 if is_video else self.config["max_file_size_mb"]

        if file_meta.size_mb > max_size:
            return QualityResult(
                decision=QualityDecision.REJECTED,
                score=0,
                reason=f"Dosya çok büyük: {file_meta.size_mb:.1f}MB (max: {max_size}MB)",
            )

        return None  # Boyut kontrolünden geçti

    def _analyze_pdf(self, file_path: str) -> PDFMetadata:
        """PDF-spesifik metadata analizi."""
        metadata = PDFMetadata()

        # Dosya yazma işleminin bitmesini bekle (watchdog bazen çok hızlı tetikleniyor)
        import time

        max_retries = 3
        for i in range(max_retries):
            try:
                # Dosya boyutunu kontrol et, 0 ise bekle
                if os.path.getsize(file_path) > 0:
                    break
                time.sleep(1)
            except Exception:
                time.sleep(1)

        # PyPDF2 ile temel analiz
        if HAS_PYPDF2:
            try:
                with open(file_path, "rb") as f:
                    reader = PdfReader(f)
                    metadata.page_count = len(reader.pages)

                    # Metadata okuma
                    if reader.metadata:
                        metadata.title = reader.metadata.get("/Title")
                        metadata.author = reader.metadata.get("/Author")
                        metadata.creation_date = reader.metadata.get("/CreationDate")

                    # Metin çıkarma (ilk birkaç sayfa)
                    total_text = ""
                    for i, page in enumerate(reader.pages[:5]):  # İlk 5 sayfa
                        try:
                            text = page.extract_text() or ""
                            total_text += text
                        except Exception:
                            pass

                    metadata.total_chars = len(total_text)
                    if metadata.page_count > 0:
                        metadata.avg_chars_per_page = metadata.total_chars / min(
                            5, metadata.page_count
                        )
                        words = len(total_text.split())
                        metadata.avg_words_per_page = words / min(
                            5, metadata.page_count
                        )

                    # OCR gerekli mi?
                    metadata.is_scannable = (
                        metadata.avg_chars_per_page < self.config["ocr_chars_threshold"]
                    )

                    # Türkçe karakter tespiti
                    turkish_chars = set("şŞğĞüÜöÖçÇıİ")
                    if any(c in total_text for c in turkish_chars):
                        metadata.language_detected = "tr"

            except Exception as e:
                # Log veya sessizce geç
                pass

        # pdfplumber ile yedek kontrol ve detaylı analiz (tablo/görsel tespiti)
        if HAS_PDFPLUMBER:
            try:
                with pdfplumber.open(file_path) as pdf:
                    # PyPDF2 başarısız olduysa veya 0 sayfa bulduysa buradan al
                    if metadata.page_count == 0:
                        metadata.page_count = len(pdf.pages)

                    for page in pdf.pages[:3]:  # İlk 3 sayfa
                        if page.images:
                            metadata.has_images = True
                        tables = page.extract_tables()
                        if tables:
                            metadata.has_tables = True
            except Exception:
                pass

        return metadata

    def _calculate_heuristic_score(
        self, file_meta: FileMetadata, pdf_meta: Optional[PDFMetadata]
    ) -> int:
        """
        Heuristik kalite skoru hesapla.

        Args:
            file_meta: Dosya metadata
            pdf_meta: PDF metadata (varsa)

        Returns:
            0-100 arası kalite skoru
        """
        score = 50  # Başlangıç skoru

        # PDF için detaylı skorlama
        if pdf_meta:
            # Sayfa sayısı değerlendirmesi
            if pdf_meta.page_count < 2:
                score -= 30
            elif pdf_meta.page_count < 5:
                score -= 5  # Kısa ama geçerli (özet, sınav sorusu vb.)
            elif pdf_meta.page_count >= 20:
                score += 15  # Kapsamlı materyal — en iyi bonus önce
            elif pdf_meta.page_count > 5:
                score += 10

            # Metin yoğunluğu — daha toleranslı eşikler
            if pdf_meta.avg_words_per_page < 10:
                score -= 25  # Neredeyse hiç metin yok (görsel ağırlıklı)
            elif pdf_meta.avg_words_per_page < 30:
                score -= 10  # Az metin, muhtemelen slayt/şema ağırlıklı
            elif pdf_meta.avg_words_per_page >= 200:
                score += 20  # Metin yoğun, akademik doküman
            elif pdf_meta.avg_words_per_page >= 80:
                score += 12  # Makul metin yoğunluğu
            elif pdf_meta.avg_words_per_page >= 40:
                score += 5  # Yeterli metin (slayt + açıklama)

            # Görsel/tablo içeriği — slayt materyalleri için olumlu
            if pdf_meta.has_images:
                score += 5  # Görsel içerik normalde derslerde bulunur
            if pdf_meta.has_tables:
                score += 5

            # Türkçe dil tespiti
            if pdf_meta.language_detected == "tr":
                score += 10

            # Metadata varlığı (profesyonel dokümanlar genelde metadata içerir)
            if pdf_meta.title:
                score += 3
            if pdf_meta.author:
                score += 2

        # Dosya boyutu — büyük dosyalar genelde içerik açısından zengindir
        if file_meta.size_mb >= 5:
            score += 5
        elif file_meta.size_mb >= 1:
            score += 3

        # Dosya adı analizi
        filename_lower = file_meta.filename.lower()

        # Pozitif anahtar kelimeler
        positive_keywords = [
            "ders",
            "not",
            "sınav",
            "vize",
            "final",
            "quiz",
            "soru",
            "çözüm",
            "özet",
            "sunum",
            "lab",
            "föy",
            "deney",
            "ödev",
            "lecture",
            "exam",
            "midterm",
            "homework",
            "solution",
        ]
        for keyword in positive_keywords:
            if keyword in filename_lower:
                score += 5
                break  # Sadece bir kez bonus

        # Negatif anahtar kelimeler
        negative_keywords = ["test", "deneme", "draft", "eski", "sil", "temp", "tmp"]
        for keyword in negative_keywords:
            if keyword in filename_lower:
                score -= 5
                break

        # Dosya yaşı (çok eski dosyalar hâlâ değerli olabilir - sınav soruları)
        if file_meta.modified_at:
            age_days = (datetime.now() - file_meta.modified_at).days
            if 30 < age_days < 3650:  # 1 ay - 10 yıl arası
                score += 5

        # Sınırları zorla
        return max(0, min(100, score))

    def get_quality_summary(self, result: QualityResult) -> str:
        """
        İnsan tarafından okunabilir kalite özeti oluştur.

        Args:
            result: QualityResult objesi

        Returns:
            Türkçe özet string
        """
        lines = []

        lines.append(f"📊 Kalite Değerlendirmesi: {result.decision.value.upper()}")
        lines.append(f"📈 Skor: {result.score}/100")
        lines.append(f"📝 Sebep: {result.reason}")

        if result.file_metadata:
            fm = result.file_metadata
            lines.append(f"📁 Dosya: {fm.filename}")
            lines.append(f"💾 Boyut: {fm.size_mb:.2f} MB")

        if result.pdf_metadata:
            pm = result.pdf_metadata
            lines.append(f"📄 Sayfa: {pm.page_count}")
            lines.append(f"📝 Ortalama kelime/sayfa: {pm.avg_words_per_page:.0f}")
            if pm.language_detected:
                lines.append(f"🌍 Dil: {pm.language_detected}")
            if pm.is_scannable:
                lines.append("🔍 OCR gerekli: Evet")

        lines.append(f"⏱️ İşlem süresi: {result.processing_time_ms:.1f}ms")

        return "\n".join(lines)


# Modül seviyesinde yardımcı fonksiyon
def quick_check(file_path: str) -> Tuple[bool, str]:
    """
    Hızlı kalite kontrolü.

    Args:
        file_path: Kontrol edilecek dosya

    Returns:
        (kabul_edildi_mi, sebep) tuple
    """
    checker = QualityChecker()
    result = checker.check_file(file_path)

    accepted = result.decision in [QualityDecision.ACCEPTED, QualityDecision.NEEDS_LLM]
    return accepted, result.reason
