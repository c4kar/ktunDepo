"""
ktunDepo Intake Agent — Report Writer
JSON rapor oluşturma — her dosya ve çalışma için detaylı kayıt.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from agent.intake.file_scanner import ScanResult
from agent.intake.llm_analyzer import AnalysisResult


@dataclass
class FileReport:
    """Tek dosya için rapor."""

    # Dosya bilgisi
    original_name: str
    new_name: Optional[str]
    original_path: str
    final_path: Optional[str]
    size_kb: float
    page_count: Optional[int]
    has_text_layer: bool
    analysis_mode: str

    # LLM analizi
    llm_analysis: Dict[str, Any]

    # Duplicate kontrolü
    duplicate_check: Optional[Dict[str, Any]]

    # Karar
    final_decision: str

    # Token kullanımı
    token_usage: Dict[str, Any]

    # Zaman damgası
    processed_at: str

    # OCR gerekli mi
    needs_ocr: bool

    # Docling gözlemleri
    docling_info: Optional[Dict[str, Any]] = None


class ReportWriter:
    """
    Rapor yazıcı.

    Her çalışma için:
    - _reports/{run_id}/summary.json — genel özet
    - _reports/{run_id}/{file}.json — dosya başına detay
    - _reports/{run_id}/ocr_queue.json — OCR bekleyen dosyalar
    """

    def __init__(self, reports_base: str = "_reports"):
        """
        ReportWriter başlat.

        Args:
            reports_base: Raporların yazılacağı ana klasör
        """
        self.reports_base = Path(reports_base)
        self.run_id: Optional[str] = None
        self.run_dir: Optional[Path] = None
        self._results: List[Dict[str, Any]] = []
        self._ocr_queue: List[Dict[str, Any]] = []
        self._token_total = {"input": 0, "output": 0}

    def start_run(self, run_id: Optional[str] = None) -> str:
        """
        Yeni bir çalışma başlat.

        Args:
            run_id: Çalışma ID'si (None ise otomatik oluşturulur)

        Returns:
            Çalışma ID'si
        """
        if run_id is None:
            run_id = f"intake_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.run_id = run_id
        self.run_dir = self.reports_base / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self._results = []
        self._ocr_queue = []
        self._token_total = {"input": 0, "output": 0}

        return run_id

    def add_file_result(
        self,
        scan_result: ScanResult,
        analysis_result: Optional[AnalysisResult],
        final_decision: str,
        new_filename: Optional[str] = None,
        final_path: Optional[str] = None,
        duplicate_result: Optional[Dict[str, Any]] = None,
        analysis_mode: str = "text",
        error: Optional[str] = None,
        docling_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Dosya sonucunu kaydet.

        Args:
            scan_result: Teknik tarama sonucu
            analysis_result: LLM analiz sonucu (None olabilir)
            final_decision: Son karar (ACCEPTED/REJECTED/REVIEW)
            new_filename: Yeni dosya adı
            final_path: Son dosya yolu
            duplicate_result: Duplicate kontrolü sonucu
            analysis_mode: Analiz modu (text/vision/metadata)
            error: Hata mesajı (varsa)
        """
        # Token kullanımını güncelle
        if analysis_result and analysis_result.tokens_used:
            self._token_total["input"] += analysis_result.tokens_used.get("input", 0)
            self._token_total["output"] += analysis_result.tokens_used.get("output", 0)

        # LLM analizini dict'e çevir
        llm_dict = {}
        if analysis_result:
            llm_dict = {
                "material_type": analysis_result.material_type,
                "course_name": analysis_result.course_name,
                "semester_guess": analysis_result.semester_guess,
                "topics": analysis_result.topics,
                "year_guess": analysis_result.year_guess,
                "has_solutions": analysis_result.has_solutions,
                "language": analysis_result.language,
                "needs_ocr": analysis_result.needs_ocr,
                "legibility": analysis_result.legibility,
                "decision": analysis_result.decision,
                "decision_reason": analysis_result.decision_reason,
                "confidence": analysis_result.confidence,
                "suggested_filename_hint": analysis_result.suggested_filename_hint,
            }

        report = FileReport(
            original_name=scan_result.filename_original,
            new_name=new_filename,
            original_path=scan_result.file_path,
            final_path=final_path,
            size_kb=scan_result.size_kb,
            page_count=scan_result.page_count,
            has_text_layer=scan_result.has_text_layer,
            analysis_mode=analysis_mode,
            llm_analysis=llm_dict,
            duplicate_check=duplicate_result,
            final_decision=final_decision,
            token_usage=analysis_result.tokens_used if analysis_result else {},
            processed_at=datetime.now().isoformat(),
            needs_ocr=analysis_result.needs_ocr if analysis_result else False,
            docling_info=docling_info,
        )

        result_dict = asdict(report)
        if error:
            result_dict["error"] = error

        self._results.append(result_dict)

        # OCR kuyruğuna ekle
        if (
            final_decision == "ACCEPTED"
            and analysis_result
            and analysis_result.needs_ocr
        ):
            self._ocr_queue.append(
                {
                    "file": final_path,
                    "material_type": analysis_result.material_type,
                    "course": analysis_result.course_name,
                    "legibility": analysis_result.legibility,
                }
            )

        # Dosya raporunu yaz
        if self.run_dir:
            safe_name = self._safe_filename(scan_result.filename_original)
            report_path = self.run_dir / f"{safe_name}.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2)

    def add_technical_rejection(
        self, file_path: str, error_type: str, error_message: str
    ) -> None:
        """
        Teknik red kaydı ekle (tarama başarısız olduğunda).

        Args:
            file_path: Dosya yolu
            error_type: Hata türü
            error_message: Hata mesajı
        """
        result = {
            "original_name": Path(file_path).name,
            "original_path": file_path,
            "final_decision": "REJECTED",
            "rejection_type": "technical",
            "error_type": error_type,
            "error_message": error_message,
            "processed_at": datetime.now().isoformat(),
            "token_usage": {},
        }
        self._results.append(result)

        # Dosya raporunu yaz
        if self.run_dir:
            safe_name = self._safe_filename(Path(file_path).name)
            report_path = self.run_dir / f"{safe_name}.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

    def finish_run(
        self, course_name: str = "", total_files: int = 0, duration_seconds: float = 0.0
    ) -> Dict[str, Any]:
        """
        Çalışmayı bitir ve özet rapor yaz.

        Args:
            course_name: İşlenen ders adı
            total_files: Toplam dosya sayısı
            duration_seconds: Toplam süre (saniye)

        Returns:
            Özet rapor dict
        """
        # İstatistikler
        accepted = sum(
            1 for r in self._results if r.get("final_decision") == "ACCEPTED"
        )
        rejected = sum(
            1 for r in self._results if r.get("final_decision") == "REJECTED"
        )
        review = sum(1 for r in self._results if r.get("final_decision") == "REVIEW")

        summary = {
            "run_id": self.run_id,
            "course": course_name,
            "started_at": datetime.now().isoformat(),
            "duration_seconds": duration_seconds,
            "total_files": total_files,
            "statistics": {
                "accepted": accepted,
                "rejected": rejected,
                "review": review,
                "ocr_queue": len(self._ocr_queue),
            },
            "token_usage": self._token_total,
            "files": [
                {
                    "name": r.get("original_name"),
                    "decision": r.get("final_decision"),
                    "new_path": r.get("final_path"),
                }
                for r in self._results
            ],
        }

        # Özet raporu yaz
        if self.run_dir:
            summary_path = self.run_dir / "summary.json"
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)

            # OCR kuyruğunu yaz
            if self._ocr_queue:
                ocr_path = self.run_dir / "ocr_queue.json"
                with open(ocr_path, "w", encoding="utf-8") as f:
                    json.dump(self._ocr_queue, f, ensure_ascii=False, indent=2)

        return summary

    def _safe_filename(self, filename: str) -> str:
        """Güvenli dosya adı oluştur."""
        # Uzantıyı kaldır ve güvenli karakterlere dönüştür
        stem = Path(filename).stem
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in stem)
        return safe[:50]  # Max 50 karakter

    def get_results(self) -> List[Dict[str, Any]]:
        """Tüm sonuçları döndür."""
        return self._results.copy()

    def get_ocr_queue(self) -> List[Dict[str, Any]]:
        """OCR kuyruğunu döndür."""
        return self._ocr_queue.copy()

    def get_token_total(self) -> Dict[str, int]:
        """Toplam token kullanımını döndür."""
        return self._token_total.copy()
