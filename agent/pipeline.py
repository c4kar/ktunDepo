"""
ktunDepo Agent — Ana Pipeline Orchestrator
LangGraph tabanlı event-driven state machine.

Event-Driven Mimari:
- SLEEPING → ACTIVE: Telegram dosyası veya _incoming'e dosya düştü
- ACTIVE → SLEEPING: İşlem tamamlandı, kuyruk boş
- ACTIVE → MAINTENANCE: Git/DB hatası, kritik sistem hatası
- MAINTENANCE → ACTIVE: Admin /resume komutu ve health check geçti
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, TypedDict, Annotated
from datetime import datetime
from enum import Enum

# Lazy imports for LangGraph
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver

    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

# Watchdog for file system events
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent

    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

# Local imports
from agent.state_manager import get_state_manager, AgentMode
from agent.config_loader import get_config
from agent.logging_config import (
    setup_logging,
    get_logger,
    log_event,
    log_material_decision,
    log_maintenance,
)
from scripts.quality_checker import QualityChecker, QualityDecision
from scripts.duplicate_detector import get_duplicate_detector, DuplicateDecision
from scripts.course_resolver import get_course_resolver, CourseNotFoundError
from scripts.git_manager import get_git_manager, get_maintenance_checker
from scripts.ocr_pipeline import get_ocr_pipeline, get_markdown_formatter
from agent.llm_evaluator import get_llm_evaluator


logger = get_logger("pipeline")


class MaterialState(TypedDict):
    """Materyal işleme state'i."""

    file_path: str
    metadata: Dict[str, Any]
    quality_result: Optional[Dict[str, Any]]
    duplicate_result: Optional[Dict[str, Any]]
    ocr_result: Optional[Dict[str, Any]]
    final_decision: Optional[str]
    final_path: Optional[str]
    error: Optional[str]
    tokens_used: int


class PipelineResult:
    """Pipeline işlem sonucu."""

    def __init__(
        self,
        success: bool,
        decision: str,
        file_path: str,
        reason: str,
        tokens_used: int = 0,
        new_path: Optional[str] = None,
    ):
        self.success = success
        self.decision = decision
        self.file_path = file_path
        self.reason = reason
        self.tokens_used = tokens_used
        self.new_path = new_path


class IncomingFileHandler(FileSystemEventHandler):
    """
    _incoming klasörünü izleyen watchdog handler.
    Yeni dosya geldiğinde agent'ı uyandırır.
    """

    def __init__(self, pipeline: "MaterialPipeline", loop: asyncio.AbstractEventLoop):
        self.pipeline = pipeline
        self.loop = loop
        self.processed_files = set()

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path

        # .gitkeep ve metadata dosyalarını atla
        if file_path.endswith((".gitkeep", ".meta.json")):
            return

        # Aynı dosyayı tekrar işleme
        if file_path in self.processed_files:
            return

        self.processed_files.add(file_path)

        # Agent'ı uyandır
        logger.info(f"Yeni dosya tespit edildi: {file_path}")

        # Ana thread'deki event loop'a thread-safe olarak gönder
        if self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self.pipeline.process_file_async(file_path), self.loop
            )
        else:
            logger.error("Event loop kapalı, dosya işlenemedi!")


class MaterialPipeline:
    """
    Materyal işleme pipeline'ı.

    Akış:
    1. Dosya analizi (heuristik kalite kontrolü)
    2. Duplicate tespiti (vektör arama)
    3. OCR (gerekirse)
    4. LLM değerlendirmesi (gerekirse)
    5. Git commit/push
    6. Sonuç bildirimi
    """

    def __init__(self, base_path: str = "."):
        """
        Pipeline başlat.

        Args:
            base_path: Depo kök dizini
        """
        self.base_path = Path(base_path)
        self.config = get_config()
        self.state_manager = get_state_manager()

        # Klasörleri oluştur
        for d in ["_incoming", "_review", "_pending", "_rejected", "_failed"]:
            (self.base_path / d).mkdir(exist_ok=True)

        # Bileşenler
        self.quality_checker = QualityChecker(
            {
                "reject_threshold": self.config.reject_threshold,
                "llm_threshold": self.config.llm_threshold,
                "min_file_size_kb": self.config.min_file_size_kb,
                "max_file_size_mb": self.config.max_file_size_mb,
                "min_pages": self.config.min_pages,
            }
        )
        self.duplicate_detector = get_duplicate_detector()
        self.course_resolver = get_course_resolver(str(base_path))
        self.git_manager = get_git_manager(str(base_path))
        self.ocr_pipeline = get_ocr_pipeline()
        self.maintenance_checker = get_maintenance_checker(str(base_path))
        self.llm_evaluator = get_llm_evaluator(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            model=self.config.llm_quality_model,
            prompts_path=self.config.prompts_path,
        )

        # Watchdog observer
        self._observer: Optional[Observer] = None

        # Logging setup
        setup_logging(log_level=self.config.log_level, log_dir=self.config.logs_path)

    def start_watching(self, loop: asyncio.AbstractEventLoop) -> bool:
        """
        _incoming klasörünü izlemeye başla.

        Args:
            loop: Ana thread'in event loop'u

        Returns:
            Başarılı mı
        """
        if not HAS_WATCHDOG:
            logger.error("watchdog modülü yüklü değil")
            return False

        incoming_path = self.base_path / self.config.incoming_path
        incoming_path.mkdir(exist_ok=True)

        self._observer = Observer()
        handler = IncomingFileHandler(self, loop)
        self._observer.schedule(handler, str(incoming_path), recursive=False)
        self._observer.start()

        logger.info(f"Klasör izleme başlatıldı: {incoming_path}")
        return True

    def stop_watching(self) -> None:
        """Klasör izlemeyi durdur."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Klasör izleme durduruldu")

    async def process_file_async(self, file_path: str) -> PipelineResult:
        """
        Dosyayı async olarak işle.

        Args:
            file_path: İşlenecek dosya yolu

        Returns:
            PipelineResult
        """
        # State'i güncelle
        if not self.state_manager.wake_up("file_created"):
            return PipelineResult(
                success=False,
                decision="SKIPPED",
                file_path=file_path,
                reason="Agent maintenance modunda",
            )

        try:
            # Metadata dosyasını önceden oku (bildirim için chat_id lazım)
            file_path_obj = Path(file_path)
            metadata = self._read_metadata(file_path_obj)

            # process_file() senkron/blocking — executor'da çalıştır
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.process_file, file_path)

            # State güncelle
            if result.decision == "ACCEPTED":
                self.state_manager.increment_processed()
            else:
                self.state_manager.increment_rejected()

            if result.tokens_used > 0:
                self.state_manager.add_token_usage(result.tokens_used)

            # Kullanıcıya bildir
            if metadata and "chat_id" in metadata:
                await self._notify_user(metadata["chat_id"], result, metadata)

            return result

        except Exception as e:
            logger.error(f"Pipeline hatası: {e}")
            return PipelineResult(
                success=False, decision="ERROR", file_path=file_path, reason=str(e)
            )
        finally:
            # Kuyrukta başka dosya yoksa uyu
            incoming_count, _ = self.maintenance_checker.check_incoming_folder()
            if incoming_count == 0:
                self.state_manager.go_to_sleep()

    async def _notify_user(
        self, chat_id: int, result: PipelineResult, metadata: Dict[str, Any]
    ) -> None:
        """Kullanıcıya işlem sonucunu bildir."""
        import httpx

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            return

        # Dosya ismini temizle (Markdown hatası için)
        filename = metadata.get("original_filename", Path(result.file_path).name)
        # Alt çizgileri kaçır
        safe_filename = (
            filename.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
        )

        if result.decision == "ACCEPTED":
            text = (
                f"✅ **Materyal Kabul Edildi!**\n\n"
                f"📁 Dosya: {safe_filename}\n"
                f"📚 Ders: {metadata.get('course', 'Bilinmiyor')}\n"
                f"📂 Konum: `{result.new_path}`\n\n"
                f"Katkınız için teşekkürler! 🙏"
            )
        elif result.decision == "REJECTED":
            text = (
                f"❌ **Materyal Reddedildi**\n\n"
                f"📁 Dosya: {safe_filename}\n"
                f"📝 Sebep: {result.reason}\n\n"
                f"Lütfen kriterlere uygun materyal gönderin."
            )
        elif result.decision == "DUPLICATE":
            text = (
                f"ℹ️ **Bu Materyal Zaten Var**\n\n"
                f"📁 Dosya: {safe_filename}\n"
                f"📝 Sebep: {result.reason}\n\n"
                f"Daha önce yüklenmiş materyaller tekrar eklenmez."
            )
        elif result.decision == "PENDING":
            text = (
                f"⏳ **Materyal Onay Bekliyor**\n\n"
                f"📁 Dosya: {safe_filename}\n"
                f"📝 Sebep: {result.reason}\n\n"
                f"Adminler materyali kontrol edip onaylayacaktır."
            )
        else:
            text = (
                f"⚠️ **İşlem Tamamlanamadı**\n\n"
                f"📁 Dosya: {safe_filename}\n"
                f"📝 Durum: {result.decision}\n"
                f"📝 Sebep: {result.reason}"
            )

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    url,
                    json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                )
        except Exception as e:
            logger.error(f"Bildirim gönderilemedi: {e}")

    def process_file(self, file_path: str) -> PipelineResult:
        """
        Dosyayı senkron olarak işle.

        Args:
            file_path: İşlenecek dosya yolu

        Returns:
            PipelineResult
        """
        file_path_obj = Path(file_path)
        total_tokens = 0

        # Metadata dosyasını oku (varsa)
        metadata = self._read_metadata(file_path_obj)

        logger.info(f"İşleniyor: {file_path_obj.name}")

        # ===== AŞAMA 1: Kalite Kontrolü =====
        quality_result = self.quality_checker.check_file(str(file_path))

        log_material_decision(
            str(file_path),
            quality_result.decision.value,
            quality_result.reason,
            quality_result.score,
        )

        # Doğrudan red
        if quality_result.decision == QualityDecision.REJECTED:
            new_path = self._move_to_status_dir(file_path_obj, "_rejected")
            self._cleanup_metadata(file_path_obj)
            return PipelineResult(
                success=True,
                decision="REJECTED",
                file_path=str(new_path),
                reason=quality_result.reason,
            )

        # OCR gerekli
        if quality_result.decision == QualityDecision.NEEDS_OCR:
            ocr_result = self.ocr_pipeline.process_pdf(str(file_path))
            if not ocr_result.success:
                new_path = self._move_to_status_dir(file_path_obj, "_failed")
                self._cleanup_metadata(file_path_obj)
                return PipelineResult(
                    success=False,
                    decision="REJECTED",
                    file_path=str(new_path),
                    reason=f"OCR başarısız: {ocr_result.error}",
                )
            # OCR metni ile devam
            text_for_duplicate = ocr_result.text[:5000]
        else:
            # PDF'den direkt metin al
            text_for_duplicate = self.ocr_pipeline.extract_text_from_pages(
                str(file_path), 0, 3
            )

        # ===== AŞAMA 2: Duplicate Kontrolü =====
        course_name = metadata.get("course") if metadata else None
        semester = self._detect_semester(file_path_obj, metadata)

        duplicate_result = self.duplicate_detector.check_duplicate(
            text_for_duplicate, semester=semester, course=course_name
        )

        if duplicate_result.decision == DuplicateDecision.DUPLICATE:
            new_path = self._move_to_status_dir(file_path_obj, "_rejected")
            self._cleanup_metadata(file_path_obj)
            log_material_decision(str(file_path), "DUPLICATE", duplicate_result.reason)
            return PipelineResult(
                success=True,
                decision="DUPLICATE",
                file_path=str(new_path),
                reason=duplicate_result.reason,
            )

        elif duplicate_result.decision == DuplicateDecision.ERROR:
            # Duplicate kontrolü başarısız oldu — güvenli taraf: _pending'e taşı
            new_path = self._move_to_status_dir(file_path_obj, "_pending")
            file_id = new_path.stem
            self.state_manager.add_pending_file(file_id, str(new_path))
            log_material_decision(
                str(file_path),
                "PENDING",
                f"Duplicate kontrol hatası: {duplicate_result.reason}",
            )
            return PipelineResult(
                success=False,
                decision="PENDING",
                file_path=str(new_path),
                reason=f"Duplicate kontrol hatası, admin incelemesi gerekli: {duplicate_result.reason}",
            )

        # ===== AŞAMA 3: Ders Yolu Belirleme =====
        try:
            if course_name:
                match = self.course_resolver.resolve(course_name, semester)
                target_dir = match.full_path
            else:
                # Ders belirtilmemişse admin onayı gerekir
                new_path = self._move_to_status_dir(file_path_obj, "_pending")
                file_id = new_path.stem
                self.state_manager.add_pending_file(file_id, str(new_path))
                return PipelineResult(
                    success=False,
                    decision="PENDING",
                    file_path=str(new_path),
                    reason="Ders bilgisi eksik, admin onayı gerekli",
                )
        except CourseNotFoundError as e:
            new_path = self._move_to_status_dir(file_path_obj, "_pending")
            file_id = new_path.stem
            self.state_manager.add_pending_file(file_id, str(new_path))
            return PipelineResult(
                success=False,
                decision="PENDING",
                file_path=str(new_path),
                reason=str(e),
            )

        # ===== AŞAMA 4: LLM Değerlendirmesi (gerekirse) =====
        needs_llm = (
            quality_result.decision == QualityDecision.NEEDS_LLM
            or duplicate_result.decision == DuplicateDecision.SIMILAR
        )

        if needs_llm:
            duplicate_similar = duplicate_result.decision == DuplicateDecision.SIMILAR
            logger.info(
                f"LLM değerlendirmesi başlatılıyor: {file_path_obj.name} "
                f"(skor={quality_result.score}, benzer={'evet' if duplicate_similar else 'hayır'})"
            )

            llm_result = self.llm_evaluator.evaluate(
                file_path=str(file_path),
                course_hint=course_name,
                material_type_hint=metadata.get("material_type") if metadata else None,
                heuristic_score=quality_result.score,
                duplicate_similar=duplicate_similar,
            )

            total_tokens += llm_result.tokens_used

            log_material_decision(
                str(file_path),
                f"LLM:{llm_result.decision}",
                llm_result.reason,
                quality_result.score,
            )

            if llm_result.decision in ("REJECT",):
                new_path = self._move_to_status_dir(file_path_obj, "_rejected")
                self._cleanup_metadata(file_path_obj)
                return PipelineResult(
                    success=True,
                    decision="REJECTED",
                    file_path=str(new_path),
                    reason=f"LLM değerlendirmesi: {llm_result.reason}",
                    tokens_used=total_tokens,
                )

            if llm_result.decision == "SIMILAR_EXISTS":
                new_path = self._move_to_status_dir(file_path_obj, "_rejected")
                self._cleanup_metadata(file_path_obj)
                log_material_decision(str(file_path), "DUPLICATE", llm_result.reason)
                return PipelineResult(
                    success=True,
                    decision="DUPLICATE",
                    file_path=str(new_path),
                    reason=f"LLM: {llm_result.reason}",
                    tokens_used=total_tokens,
                )

            # ACCEPT — devam
            final_decision = "ACCEPTED"
        else:
            final_decision = "ACCEPTED"

        # ===== AŞAMA 5: Dosya Taşıma =====
        material_type = metadata.get("material_type", "Diğer") if metadata else "Diğer"

        # Manuel kontrol aktifse _review klasörüne taşı
        if self.config.manual_review:
            review_path = self._move_to_status_dir(file_path_obj, "_review")
            file_id = review_path.stem
            self.state_manager.add_review_file(file_id, str(review_path))

            log_material_decision(
                str(file_path),
                "ACCEPTED",
                f"Review bekliyor: {review_path.name}",
                quality_result.score,
            )

            return PipelineResult(
                success=True,
                decision="ACCEPTED",
                file_path=str(review_path),
                reason="Materyal kabul edildi, kullanıcı onayı bekliyor",
                tokens_used=total_tokens,
                new_path=str(review_path),
            )

        try:
            success, new_path = self.git_manager.move_file_to_course(
                str(file_path), target_dir, file_path_obj.name
            )

            if not success:
                failed_path = self._move_to_status_dir(file_path_obj, "_failed")
                return PipelineResult(
                    success=False,
                    decision="ERROR",
                    file_path=str(failed_path),
                    reason=f"Dosya taşıma hatası: {new_path}",
                    tokens_used=total_tokens,
                )

            # Metadata dosyasını temizle
            self._cleanup_metadata(file_path_obj)

            # ===== AŞAMA 6: Git Commit =====
            if self.config.git_auto_commit:
                course_code = course_name or "unknown"
                git_result = self.git_manager.commit_material(
                    new_path, course_code, material_type
                )

                if not git_result.success:
                    # Geri al
                    logger.error(
                        f"Git commit başarısız, rollback yapılıyor: {git_result.error}"
                    )
                    import shutil

                    failed_dir = self.base_path / "_failed"
                    failed_dir.mkdir(exist_ok=True)
                    failed_path = failed_dir / Path(new_path).name
                    shutil.move(new_path, str(failed_path))

                    log_maintenance("git commit failed", git_result.error)
                    return PipelineResult(
                        success=False,
                        decision="ERROR",
                        file_path=str(failed_path),
                        reason=f"Git commit hatası, geri alındı: {git_result.error}",
                        tokens_used=total_tokens,
                    )

            # ===== AŞAMA 7: Vektör DB'ye Ekle =====
            if text_for_duplicate:
                self.duplicate_detector.add_document(
                    text_for_duplicate,
                    {
                        "semester": semester,
                        "course": course_name,
                        "filename": file_path_obj.name,
                        "path": new_path,
                        "material_type": material_type,
                    },
                )

            log_material_decision(
                str(file_path), "ACCEPTED", f"Eklendi: {new_path}", quality_result.score
            )

            return PipelineResult(
                success=True,
                decision="ACCEPTED",
                file_path=str(file_path),
                reason=f"Başarıyla eklendi",
                tokens_used=total_tokens,
                new_path=new_path,
            )
        except Exception as e:
            logger.error(f"Beklenmeyen hata: {e}")
            failed_path = self._move_to_status_dir(file_path_obj, "_failed")
            return PipelineResult(
                success=False,
                decision="ERROR",
                file_path=str(failed_path),
                reason=f"Beklenmeyen hata: {e}",
                tokens_used=total_tokens,
            )

    def _read_metadata(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Metadata dosyasını oku."""
        meta_path = file_path.with_suffix(file_path.suffix + ".meta.json")
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _cleanup_metadata(self, file_path: Path) -> None:
        """Metadata dosyasını sil."""
        meta_path = file_path.with_suffix(file_path.suffix + ".meta.json")
        if meta_path.exists():
            try:
                meta_path.unlink()
            except Exception:
                pass

    def _cleanup_file(self, file_path: Path) -> None:
        """Dosya ve metadata'yı sil."""
        try:
            if file_path.exists():
                file_path.unlink()
            self._cleanup_metadata(file_path)
        except Exception:
            pass

    def _move_to_status_dir(self, file_path: Path, status_dir: str) -> Path:
        """Dosyayı ve meta dosyasını ilgili durum klasörüne taşı."""
        import shutil

        target_dir = self.base_path / status_dir
        target_dir.mkdir(exist_ok=True)

        target_path = target_dir / file_path.name

        # Eğer hedefte aynı isimde dosya varsa ismini değiştir
        counter = 1
        while target_path.exists():
            target_path = target_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
            counter += 1

        try:
            shutil.move(str(file_path), str(target_path))

            # Meta dosyası varsa onu da taşı
            meta_path = file_path.with_suffix(file_path.suffix + ".meta.json")
            if meta_path.exists():
                target_meta = target_path.with_suffix(target_path.suffix + ".meta.json")
                shutil.move(str(meta_path), str(target_meta))

            return target_path
        except Exception as e:
            logger.error(f"Dosya taşıma hatası {file_path} -> {status_dir}: {e}")
            return file_path

    def _detect_semester(
        self, file_path: Path, metadata: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Dönem bilgisini tespit et."""
        # Metadata'dan
        if metadata and "semester" in metadata:
            return metadata["semester"]

        # Dosya yolundan
        for part in file_path.parts:
            if part.startswith("EEM-"):
                return part

        return None

    def run_health_check(self) -> Dict[str, Any]:
        """
        Sistem sağlık kontrolü yap.

        Returns:
            Sağlık raporu
        """
        report = self.maintenance_checker.run_health_check()

        # Qdrant kontrolü
        try:
            stats = self.duplicate_detector.get_collection_stats()
            if "error" in stats:
                report["healthy"] = False
                report["issues"].append(f"Qdrant: {stats['error']}")
            else:
                report["vector_db"] = stats
        except Exception as e:
            report["healthy"] = False
            report["issues"].append(f"Qdrant bağlantı hatası: {str(e)}")

        # State güncelle
        self.state_manager.update_health_check()

        # Sağlıksızsa maintenance moduna geç
        if not report["healthy"] and report["issues"]:
            self.state_manager.enter_maintenance("; ".join(report["issues"]))

        return report

    def process_pending_files(self) -> List[PipelineResult]:
        """
        Bekleyen tüm dosyaları işle.

        Returns:
            İşlem sonuçları listesi
        """
        incoming_path = self.base_path / self.config.incoming_path
        results = []

        for file_path in incoming_path.iterdir():
            if file_path.is_file() and not file_path.name.endswith(
                (".gitkeep", ".meta.json")
            ):
                result = self.process_file(str(file_path))
                results.append(result)

        return results


def create_pipeline() -> MaterialPipeline:
    """Pipeline instance oluştur."""
    base_path = os.getenv("AGENT_BASE_PATH", ".")
    return MaterialPipeline(base_path)


# Ana entry point
if __name__ == "__main__":
    import sys

    pipeline = create_pipeline()

    if len(sys.argv) > 1:
        # Tek dosya işle
        file_path = sys.argv[1]
        result = pipeline.process_file(file_path)
        print(f"Sonuç: {result.decision}")
        print(f"Sebep: {result.reason}")
    else:
        # Watchdog modu
        print("🤖 ktunDepo Agent başlatılıyor...")

        # Async loop oluştur
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if pipeline.start_watching(loop):
            print("📁 _incoming klasörü izleniyor. Ctrl+C ile durdurun.")
            try:
                loop.run_forever()
            except KeyboardInterrupt:
                pipeline.stop_watching()
                print("\n👋 Agent durduruldu.")
        else:
            print("❌ Watchdog başlatılamadı")
