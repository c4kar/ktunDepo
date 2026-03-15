"""
ktunDepo Intake Agent — Filename Generator
Standart dosya adı üretimi.

Format: {tür}_{konu_slug}_{yıl}_v{n}.{ext}
Örnek: sinav_vektorler-moment_2022_v1.pdf
"""

import os
import re
from pathlib import Path
from typing import Optional

from agent.intake.llm_analyzer import AnalysisResult


class FilenameGenerator:
    """Standart dosya adı üretici."""

    # Materyal türü → prefix eşlemesi
    TYPE_PREFIX = {
        "ders_notu": "not",
        "lms_sunumu": "lms",
        "sinav_sorusu": "sinav",
        "sinav_cozumu": "cozum",
        "laboratuvar_foyu": "lab",
        "ozet": "ozet",
        "video_ders": "video",
        "diger": "materyal",
    }

    # Türkçe karakter dönüşümü
    TURKISH_CHARS = str.maketrans("ıİğĞşŞçÇöÖüÜ", "iiggssccoouu")

    def generate(
        self, analysis: AnalysisResult, extension: str, target_dir: str
    ) -> str:
        """
        Standart dosya adı üret.

        Args:
            analysis: LLM analiz sonucu
            extension: Dosya uzantısı (.pdf, .pptx, vb.)
            target_dir: Hedef klasör (versiyon kontrolü için)

        Returns:
            Yeni dosya adı (uzantı dahil)
        """
        prefix = self.TYPE_PREFIX.get(analysis.material_type, "materyal")

        # Konu slug'ı
        topic_slug = self._generate_topic_slug(analysis)

        # Yıl
        year = analysis.year_guess or "tarihsiz"

        # Temel isim
        base = f"{prefix}_{topic_slug}_{year}_{analysis.quality_score}Star"

        # Versiyon kontrolü
        version = 1
        while True:
            candidate = f"{base}_v{version}{extension}"
            if not os.path.exists(os.path.join(target_dir, candidate)):
                return candidate
            version += 1
            if version > 100:  # Güvenlik sınırı
                break

        return f"{base}_v{version}{extension}"

    def _generate_topic_slug(self, analysis: AnalysisResult) -> str:
        """Konu slug'ı üret."""
        # Önce LLM'in önerdiği hint'i dene
        if analysis.suggested_filename_hint:
            slug = self._slugify(analysis.suggested_filename_hint)
            if len(slug) >= 3:
                return slug[:30]

        # Topics'ten üret
        if analysis.topics:
            combined = "-".join(analysis.topics[:2])
            slug = self._slugify(combined)
            if len(slug) >= 3:
                return slug[:30]

        # Ders adından üret
        if analysis.course_name:
            slug = self._slugify(analysis.course_name)
            if len(slug) >= 3:
                return slug[:20]

        return "genel"

    def _slugify(self, text: str) -> str:
        """Metni URL-safe slug'a çevir."""
        text = text.lower().translate(self.TURKISH_CHARS)
        text = re.sub(r"[^a-z0-9\s-]", "", text)
        text = re.sub(r"\s+", "-", text.strip())
        text = re.sub(r"-+", "-", text)  # Çoklu tire'yi tekile indir
        return text[:40]

    def generate_from_original(
        self, original_name: str, analysis: AnalysisResult, target_dir: str
    ) -> str:
        """
        Orijinal dosya adını koruyarak üret (fallback).

        Args:
            original_name: Orijinal dosya adı
            analysis: LLM analiz sonucu
            target_dir: Hedef klasör

        Returns:
            Temizlenmiş dosya adı
        """
        path = Path(original_name)
        extension = path.suffix.lower()
        stem = path.stem

        # Türkçe karakterleri değiştir ve temizle
        clean_stem = self._slugify(stem)

        if len(clean_stem) < 3:
            clean_stem = "materyal"

        # Versiyon kontrolü
        version = 1
        while True:
            if version == 1:
                candidate = f"{clean_stem}{extension}"
            else:
                candidate = f"{clean_stem}_v{version}{extension}"

            if not os.path.exists(os.path.join(target_dir, candidate)):
                return candidate
            version += 1
            if version > 100:
                break

        return f"{clean_stem}_v{version}{extension}"
