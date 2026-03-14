"""
ktunDepo Agent — Course Path Resolver
Ders adı ve dönem bilgisinden dosya yolunu çözen modül.
Fuzzy matching ile öğrenci girdilerini mevcut klasör yapısıyla eşleştirir.
"""

import os
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

# Fuzzy matching için lazy import
try:
    from rapidfuzz import fuzz, process

    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False
    # Fallback: difflib
    from difflib import get_close_matches


class CourseNotFoundError(Exception):
    """Ders klasörü bulunamadı hatası."""

    pass


@dataclass
class CourseMatch:
    """Ders eşleştirme sonucu."""

    course_name: str  # Eşleşen klasör adı
    semester: str  # Dönem (EEM-1, EEM-2, ...)
    full_path: str  # Tam dosya yolu
    confidence: float  # Eşleşme güveni (0-100)
    is_exact: bool  # Tam eşleşme mi


class CourseResolver:
    """
    Ders adı ve dönem bilgisinden dosya yolu çözen sınıf.

    Mevcut depo yapısını okuyarak fuzzy matching ile
    öğrenci girdilerini doğru klasörlerle eşleştirir.
    """

    # Türkçe karakter normalizasyonu
    TURKISH_CHAR_MAP = {
        "ş": "s",
        "Ş": "S",
        "ğ": "g",
        "Ğ": "G",
        "ü": "u",
        "Ü": "U",
        "ö": "o",
        "Ö": "O",
        "ç": "c",
        "Ç": "C",
        "ı": "i",
        "İ": "I",
    }

    # Yaygın kısaltmalar ve alternatifleri
    COURSE_ALIASES = {
        "mat": ["matematik", "mat1", "mat2", "matematik 1", "matematik 2"],
        "fizik": ["fiz", "fizik 1", "fizik 2", "fiz1", "fiz2"],
        "kimya": ["kim", "genel kimya"],
        "lineer": ["lineer cebir", "cebir", "linear algebra"],
        "devre": ["devre analizi", "devre analiz", "circuit analysis"],
        "difdent": ["diferansiyel denklemler", "diff denklem", "difdenklem", "ode"],
        "elektronik": ["elekt", "elektrik", "electronics"],
        "lojik": ["lojik devreler", "sayısal devreler", "dijital", "digital"],
        "bilgisayar": ["bilgisayar programlama", "bp", "programlama", "python", "c++"],
        "teknik resim": ["bilgisayar destekli teknik resim", "autocad", "cad"],
        "atatürk": ["atatürk ilkeleri", "inkılap tarihi", "tarih"],
        "iş sağlığı": ["iş güvenliği", "isg"],
        "mekanik": ["mühendislik mekaniği", "statik", "mechanics"],
        "sinyal": ["sinyal sistemler", "signal", "sayisal isaret", "dsp"],
        "kontrol": ["kontrol sistemleri", "otomatik kontrol", "control systems"],
        "iletisim": ["haberlesme", "communications", "telekomunikasyon"],
        "mikro": ["mikroislemciler", "mikrodenetleyici", "microcontroller", "arduino"],
        "em": ["elektromanyetik", "electromagnetics", "alan teorisi"],
        "termodinamik": ["termo", "thermodynamics"],
        "olasılık": ["olasilik", "istatistik", "probability", "statistics"],
    }

    def __init__(self, base_path: str = "."):
        """
        CourseResolver başlat.

        Args:
            base_path: Depo kök dizini
        """
        self.base_path = Path(base_path)
        self._course_cache: dict = {}
        self._refresh_cache()

    def _refresh_cache(self) -> None:
        """Mevcut ders klasörlerini önbelleğe al."""
        self._course_cache = {}

        # EEM-X klasörlerini tara
        for semester_dir in self.base_path.iterdir():
            if semester_dir.is_dir() and semester_dir.name.startswith("EEM-"):
                semester = semester_dir.name
                self._course_cache[semester] = []

                for course_dir in semester_dir.iterdir():
                    if course_dir.is_dir():
                        self._course_cache[semester].append(course_dir.name)

    def _normalize_text(self, text: str) -> str:
        """Türkçe karakterleri ve büyük/küçük harfleri normalize et."""
        text = text.lower().strip()
        for tr_char, ascii_char in self.TURKISH_CHAR_MAP.items():
            text = text.replace(tr_char.lower(), ascii_char.lower())
        return text

    def _expand_aliases(self, query: str) -> List[str]:
        """Kısaltmaları genişlet."""
        normalized = self._normalize_text(query)
        candidates = [query]

        for key, aliases in self.COURSE_ALIASES.items():
            if normalized in self._normalize_text(key) or any(
                normalized in self._normalize_text(a) for a in aliases
            ):
                candidates.extend(aliases)

        return list(set(candidates))

    def resolve(
        self,
        course_query: str,
        semester: Optional[str] = None,
        min_confidence: float = 55.0,
    ) -> CourseMatch:
        """
        Ders adını mevcut klasör yapısıyla eşleştir.

        Args:
            course_query: Öğrencinin yazdığı ders adı
            semester: Dönem (örn: "EEM-1"). None ise tüm dönemlerde ara.
            min_confidence: Minimum eşleşme güveni (0-100)

        Returns:
            CourseMatch objesi

        Raises:
            CourseNotFoundError: Eşleşme bulunamazsa
        """
        # Önbellek boşsa yenile
        if not self._course_cache:
            self._refresh_cache()

        # Arama yapılacak dönemleri belirle
        semesters_to_search = (
            [semester]
            if semester and semester in self._course_cache
            else list(self._course_cache.keys())
        )

        best_match: Optional[CourseMatch] = None
        best_score = 0.0

        # Kısaltmaları genişlet
        queries = self._expand_aliases(course_query)
        # Normalize edilmiş sorguları da ekle
        normalized_queries = list({self._normalize_text(q) for q in queries})

        for sem in semesters_to_search:
            courses = self._course_cache.get(sem, [])
            if not courses:
                continue

            normalized_courses = [self._normalize_text(c) for c in courses]

            for query in queries:
                normalized_query = self._normalize_text(query)

                # Tam eşleşme kontrolü (normalize edilmiş)
                for i, course in enumerate(courses):
                    if normalized_query == normalized_courses[i]:
                        return CourseMatch(
                            course_name=course,
                            semester=sem,
                            full_path=str(self.base_path / sem / course),
                            confidence=100.0,
                            is_exact=True,
                        )

                # İçerik eşleşmesi: sorgu, klasör adının içinde mi?
                for i, course in enumerate(courses):
                    if (
                        normalized_query in normalized_courses[i]
                        or normalized_courses[i] in normalized_query
                    ):
                        score = 85.0
                        if score > best_score:
                            best_score = score
                            best_match = CourseMatch(
                                course_name=course,
                                semester=sem,
                                full_path=str(self.base_path / sem / course),
                                confidence=score,
                                is_exact=False,
                            )

                # Fuzzy eşleştirme
                if HAS_RAPIDFUZZ:
                    # WRatio: genel amaçlı en iyi scorer
                    match_wratio = process.extractOne(
                        normalized_query,
                        normalized_courses,
                        scorer=fuzz.WRatio,
                        score_cutoff=min_confidence,
                    )
                    if match_wratio:
                        _, score, idx = match_wratio
                        if score > best_score:
                            best_score = score
                            best_match = CourseMatch(
                                course_name=courses[idx],
                                semester=sem,
                                full_path=str(self.base_path / sem / courses[idx]),
                                confidence=score,
                                is_exact=False,
                            )

                    # token_set_ratio: kelime sırasından bağımsız, kısmi eşleşmeler için iyi
                    match_token = process.extractOne(
                        normalized_query,
                        normalized_courses,
                        scorer=fuzz.token_set_ratio,
                        score_cutoff=min_confidence,
                    )
                    if match_token:
                        _, score, idx = match_token
                        # token_set_ratio sonuçlarını hafif indir (daha agresif scorer)
                        adjusted_score = score * 0.95
                        if adjusted_score > best_score:
                            best_score = adjusted_score
                            best_match = CourseMatch(
                                course_name=courses[idx],
                                semester=sem,
                                full_path=str(self.base_path / sem / courses[idx]),
                                confidence=adjusted_score,
                                is_exact=False,
                            )
                else:
                    # difflib ile (fallback)
                    matches = get_close_matches(
                        normalized_query,
                        normalized_courses,
                        n=1,
                        cutoff=min_confidence / 100,
                    )
                    if matches:
                        # Orijinal isimleri bul
                        try:
                            idx = normalized_courses.index(matches[0])
                            score = 70.0  # difflib kesin skor vermez
                            if score > best_score:
                                best_score = score
                                best_match = CourseMatch(
                                    course_name=courses[idx],
                                    semester=sem,
                                    full_path=str(self.base_path / sem / courses[idx]),
                                    confidence=score,
                                    is_exact=False,
                                )
                        except ValueError:
                            pass

        if best_match:
            return best_match

        # Eşleşme bulunamadı
        raise CourseNotFoundError(
            f"'{course_query}' için ders klasörü bulunamadı. "
            f"Mevcut dönemler: {', '.join(semesters_to_search)}"
        )

    def list_courses(self, semester: Optional[str] = None) -> dict:
        """
        Mevcut ders klasörlerini listele.

        Args:
            semester: Belirli dönem (None ise tümü)

        Returns:
            {dönem: [ders listesi]} şeklinde dict
        """
        if not self._course_cache:
            self._refresh_cache()

        if semester:
            return {semester: self._course_cache.get(semester, [])}
        return self._course_cache.copy()

    def suggest_path(
        self, course_query: str, semester: str, material_type: str, filename: str
    ) -> str:
        """
        Materyal için önerilen tam dosya yolu oluştur.

        Args:
            course_query: Ders adı
            semester: Dönem
            material_type: Materyal türü
            filename: Dosya adı

        Returns:
            Önerilen dosya yolu
        """
        try:
            match = self.resolve(course_query, semester)
            base_path = match.full_path

            # LMS materyalleri için özel klasör
            if material_type.lower() in ["sunum", "lms"]:
                lms_path = Path(base_path) / "LMS"
                if lms_path.exists():
                    return str(lms_path / filename)

            return str(Path(base_path) / filename)

        except CourseNotFoundError:
            # Yeni klasör önerisi (admin onayı gerekir)
            safe_course = course_query.replace(" ", "_").replace("/", "-")
            return f"{semester}/{safe_course}/{filename}"

    def get_semester_from_path(self, file_path: str) -> Optional[str]:
        """Dosya yolundan dönem bilgisini çıkar."""
        path = Path(file_path)
        parts = path.parts

        for part in parts:
            if part.startswith("EEM-"):
                return part
        return None

    def get_course_from_path(self, file_path: str) -> Optional[str]:
        """Dosya yolundan ders adını çıkar."""
        path = Path(file_path)
        parts = path.parts

        for i, part in enumerate(parts):
            if part.startswith("EEM-") and i + 1 < len(parts):
                return parts[i + 1]
        return None


# Singleton instance
_resolver: Optional[CourseResolver] = None


def get_course_resolver(base_path: str = ".") -> CourseResolver:
    """Global CourseResolver instance döndür."""
    global _resolver
    if _resolver is None:
        _resolver = CourseResolver(base_path)
    return _resolver
