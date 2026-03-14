"""
ktunDepo Intake Agent — Path Resolver
Hedef yol tespiti — EEM-X/{Ders}/{alt_klasör}/ yolunu belirler.
"""

import os
from pathlib import Path
from typing import Optional, List, Tuple

from rapidfuzz import process as fuzz_process

from agent.intake.llm_analyzer import AnalysisResult
from agent.intake.hint_loader import IntakeHint


class PathResolutionError(Exception):
    """Yol çözümleme hatası."""

    pass


class SemesterUnknownError(PathResolutionError):
    """Dönem tespit edilemedi."""

    pass


class CourseMatchError(PathResolutionError):
    """Ders eşleştirilemedi."""

    pass


class PathResolver:
    """
    Hedef yol çözümleyici.

    Akış:
    1. Dönem tespiti (intake klasör adından veya LLM'den)
    2. Ders adı fuzzy match
    3. Alt klasör belirleme (LMS sunumları için LMS/)
    """

    SEMESTERS = ["EEM-1", "EEM-2", "EEM-3", "EEM-4", "EEM-5", "EEM-6", "EEM-7", "EEM-8"]

    FUZZY_MATCH_THRESHOLD = 65  # %65 altı eşleşmelerde hata (türkçe karakter toleransı için düşürüldü)

    def __init__(self, repo_root: str):
        """
        PathResolver başlat.

        Args:
            repo_root: Depo kök dizini
        """
        self.repo_root = Path(repo_root)

    def resolve(
        self, analysis: AnalysisResult, intake_folder: str, new_filename: str, hint: Optional[IntakeHint] = None
    ) -> Tuple[str, str]:
        """
        Hedef yolu belirle.

        Args:
            analysis: LLM analiz sonucu
            intake_folder: Kaynak _intake klasörü (dönem tespiti için)
            new_filename: Yeni dosya adı

        Returns:
            (target_dir, target_path) tuple

        Raises:
            PathResolutionError: Yol belirlenemezse
        """
        # 1. Dönem tespiti
        semester = self._detect_semester(intake_folder, analysis, hint)
        if not semester:
            raise SemesterUnknownError(
                f"Dönem tespit edilemedi. intake_folder={intake_folder}, "
                f"llm_guess={analysis.semester_guess}"
            )

        # 2. Ders adı eşleştirme
        course_name_to_match = hint.course if hint and hint.course else analysis.course_name
        course = self._match_course(course_name_to_match, semester)
        if not course:
            raise CourseMatchError(
                f"Ders eşleştirilemedi: '{analysis.course_name}' (dönem: {semester})"
            )

        # 3. Alt klasör belirleme
        if analysis.material_type == "lms_sunumu":
            target_dir = self.repo_root / semester / course / "LMS"
        else:
            target_dir = self.repo_root / semester / course

        # Klasörü oluştur
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / new_filename

        return str(target_dir), str(target_path)

    def _detect_semester(
        self, intake_folder: str, analysis: AnalysisResult, hint: Optional[IntakeHint] = None
    ) -> Optional[str]:
        """Dönem tespit et."""
        # 0. Kullanıcı Hint dosyası varsa kesin kabul et
        if hint and hint.semester:
            if hint.semester in self.SEMESTERS:
                return hint.semester
            # else: eğer geçersizse fallback yapalım

        # Önce intake klasör adından dene
        # _intake/EEM-1/Fizik/ → EEM-1
        intake_path = Path(intake_folder)
        for part in intake_path.parts:
            if part in self.SEMESTERS:
                return part

        # LLM tahmininden
        if analysis.semester_guess in self.SEMESTERS:
            return analysis.semester_guess

        # Ders adından tahmin et
        semester = self._guess_semester_from_course(analysis.course_name)
        if semester:
            return semester

        return None

    def _guess_semester_from_course(self, course_name: str) -> Optional[str]:
        """Ders adından dönem tahmin et."""
        if not course_name:
            return None

        course_lower = course_name.lower()

        # EEM-1 dersleri (hem Türkçe hem kebab-case ASCII karşılıkları)
        eem1_courses = [
            "fizik",
            "matematik",
            "kimya",
            "lineer cebir",
            "lineer-cebir",
            "linear algebra",
            "bilgisayar programlama 1",
            "bilgisayar-programlama-1",
            "teknik resim",
            "bilgisayar destekli teknik resim",
            "bilgisayar-destekli-teknik-resim",
            "atatürk",
            "ataturk",
            "inkilap",
        ]
        for c in eem1_courses:
            if c in course_lower:
                return "EEM-1"

        # EEM-2 dersleri (hem Türkçe hem kebab-case ASCII karşılıkları)
        eem2_courses = [
            "devre analizi",
            "devre-analizi",
            "diferansiyel denklemler",
            "diferansiyel-denklemler",
            "diferansiyel",
            "difdenk",
            "mühendislik mekaniği",
            "muhendislik-mekanigi",
            "mühendislik mekanigi",
            "lojik devreler",
            "lojik-devreler",
            "elektronik",
            "iş sağlığı",
            "is-sagligi",
            "is sagligi",
        ]
        for c in eem2_courses:
            if c in course_lower:
                return "EEM-2"

        # Her dönemde hangi derslerin olduğunu kontrol et
        for semester in self.SEMESTERS:
            semester_path = self.repo_root / semester
            if semester_path.exists():
                courses = self.list_courses(semester)
                for existing_course in courses:
                    if course_lower in existing_course.lower():
                        return semester

        return None

    # Kısa kısaltma → tam kebab-case adı ön-çeviri tablosu
    COURSE_ALIASES: dict = {
        "difdenk": "diferansiyel-denklemler",
        "diferansiyel denklemler": "diferansiyel-denklemler",
        "diferansiyel": "diferansiyel-denklemler",
        "devre analizi ii": "devre-analizi-2",
        "devre analizi 2": "devre-analizi-2",
        "devre analizi i": "devre-analizi",
        "devre analizi": "devre-analizi",
        "lojik devreler": "lojik-devreler",
        "lineer cebir": "lineer-cebir",
        "linear algebra": "lineer-cebir",
        "muhendislik mekanigi": "muhendislik-mekanigi",
        "mühendislik mekaniği": "muhendislik-mekanigi",
        "is sagligi": "is-sagligi",
        "iş sağlığı": "is-sagligi",
        "bilgisayar programlama 1": "bilgisayar-programlama-1",
        "bilgisayar programlama": "bilgisayar-programlama",
        "teknik resim": "bilgisayar-destekli-teknik-resim",
        "ataturk": "ataturk-ilkeleri-ve-inkilap-tarihi",
        "atatürk": "ataturk-ilkeleri-ve-inkilap-tarihi",
        "inkilap tarihi": "ataturk-ilkeleri-ve-inkilap-tarihi",
    }

    def _match_course(self, course_guess: str, semester: str) -> Optional[str]:
        """Ders adını fuzzy match ile eşleştir."""
        if not course_guess:
            return None

        available = self.list_courses(semester)
        if not available:
            return None

        # Alias ön-çevirisi: kısa kısaltmaları tam ada dönüştür
        normalized = self.COURSE_ALIASES.get(course_guess.lower(), course_guess)

        # Alias doğrudan bir klasör adına karşılık geliyorsa kesin eşleşme
        if normalized in available:
            return normalized

        # Fuzzy match (normalize edilmiş isimle)
        result = fuzz_process.extractOne(normalized, available)
        if result:
            match, score, _ = result
            if score >= self.FUZZY_MATCH_THRESHOLD:
                return match

        return None

    def list_courses(self, semester: str) -> List[str]:
        """Bir dönemdeki mevcut ders klasörlerini listele."""
        semester_path = self.repo_root / semester
        if not semester_path.exists():
            return []

        courses = []
        for item in semester_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                courses.append(item.name)

        return courses

    def list_all_courses(self) -> dict:
        """Tüm dönemlerdeki dersleri listele."""
        result = {}
        for semester in self.SEMESTERS:
            courses = self.list_courses(semester)
            if courses:
                result[semester] = courses
        return result

    def get_target_for_review(
        self, course_name: str, review_base: str = "_review"
    ) -> str:
        """Review klasörü için hedef yol."""
        target = self.repo_root / review_base / (course_name or "unknown")
        target.mkdir(parents=True, exist_ok=True)
        return str(target)

    def get_target_for_rejected(
        self, course_name: str, rejected_base: str = "_rejected"
    ) -> str:
        """Rejected klasörü için hedef yol."""
        target = self.repo_root / rejected_base / (course_name or "unknown")
        target.mkdir(parents=True, exist_ok=True)
        return str(target)
