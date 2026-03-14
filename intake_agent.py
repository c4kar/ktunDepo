#!/usr/bin/env python3
"""
ktunDepo Intake Agent — Toplu Materyal Alım CLI

_intake/ klasörüne yığılan materyalleri analiz edip
uygun klasörlere taşıyan LLM-first pipeline.

Kullanım:
    python intake_agent.py run                 # Normal çalıştırma
    python intake_agent.py run --dry-run       # Sadece analiz, taşıma yok
    python intake_agent.py run --file X.pdf    # Tek dosya işle
    python intake_agent.py status              # Kuyruk durumu
    python intake_agent.py report              # Son raporu göster
"""

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

try:
    import typer
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
except ImportError:
    print("Gerekli paketler eksik. Kurulum:")
    print("  pip install typer rich")
    sys.exit(1)

from agent.intake import (
    FileScanner,
    ScanResult,
    TechnicalError,
    ContentPreparer,
    PreparedContent,
    LLMAnalyzer,
    AnalysisResult,
    FilenameGenerator,
    PathResolver,
    ReportWriter,
    DoclingGateway,
)
from agent.intake.hint_loader import HintLoader
from agent.config_loader import get_config
from agent.intake.content_preparer import ContentMode

# Duplicate detector import (optional - Qdrant olmayabilir)
HAS_DUPLICATE_DETECTOR = False
_DuplicateDetector: Any = None
_DuplicateDecision: Any = None

try:
    from scripts.duplicate_detector import (
        DuplicateDetector as _DD,
        DuplicateDecision as _DDec,
    )

    _DuplicateDetector = _DD
    _DuplicateDecision = _DDec
    HAS_DUPLICATE_DETECTOR = True
except ImportError:
    pass

    class DuplicateDecision:  # type: ignore
        DUPLICATE = "duplicate"
        SIMILAR = "similar"
        UNIQUE = "unique"

    class DuplicateResult:  # type: ignore
        pass


# === Paths ===
REPO_ROOT = Path(__file__).parent
INTAKE_DIR = REPO_ROOT / "_intake"
REJECTED_DIR = REPO_ROOT / "_rejected"
REVIEW_DIR = REPO_ROOT / "_review"
REPORTS_DIR = REPO_ROOT / "_reports"

# === CLI Setup ===
app = typer.Typer(
    name="intake-agent",
    help="ktunDepo Toplu Materyal Alım Ajanı",
    no_args_is_help=True,
)
console = Console()


class ProcessingStatus(Enum):
    """Dosya işleme durumu."""

    SUCCESS = "success"
    REJECTED = "rejected"
    REVIEW = "review"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class ProcessingResult:
    """Tek dosya için işleme sonucu."""

    original_path: Path
    status: ProcessingStatus
    final_path: Optional[Path] = None
    analysis: Optional[AnalysisResult] = None
    generated_filename: Optional[str] = None
    error_message: Optional[str] = None
    duplicate_info: Optional[dict] = None
    docling_info: Optional[dict] = None


@dataclass
class BatchResult:
    """Toplu işleme sonucu."""

    processed: List[ProcessingResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.processed if r.status == ProcessingStatus.SUCCESS)

    @property
    def rejected_count(self) -> int:
        return sum(1 for r in self.processed if r.status == ProcessingStatus.REJECTED)

    @property
    def review_count(self) -> int:
        return sum(1 for r in self.processed if r.status == ProcessingStatus.REVIEW)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.processed if r.status == ProcessingStatus.ERROR)


class IntakeAgent:
    """
    Ana intake agent orchestrator.

    Pipeline:
    1. Technical scan (sadece bozuk dosyaları ele)
    2. Content preparation (metin/görsel hazırla)
    3. LLM analysis (Claude ile analiz)
    4. Duplicate check (Qdrant ile kontrol)
    5. Filename generation (standart format)
    6. Path resolution (hedef klasör)
    7. File move (veya dry-run)
    8. Report generation
    """

    def __init__(
        self,
        dry_run: bool = False,
        verbose: bool = False,
        skip_duplicates: bool = True,
    ):
        self.dry_run = dry_run
        self.verbose = verbose
        self.skip_duplicates = skip_duplicates
        self.config = get_config()

        # Components
        self.scanner = FileScanner()
        self.preparer = ContentPreparer()
        self.analyzer = LLMAnalyzer()
        self.filename_gen = FilenameGenerator()
        self.path_resolver = PathResolver(repo_root=str(REPO_ROOT))
        self.report_writer = ReportWriter(reports_base=str(REPORTS_DIR))
        self.hint_loader = HintLoader(intake_root=str(INTAKE_DIR))

        self.docling_gateway: Optional[DoclingGateway] = None
        if self.config.docling_enabled:
            self.docling_gateway = DoclingGateway(
                min_extracted_chars=self.config.docling_min_extracted_chars,
                optimize_pdf_over_mb=self.config.docling_optimize_pdf_over_mb,
                optimize_min_saving_percent=self.config.docling_optimize_min_saving_percent,
                optimize_max_pages=self.config.docling_optimize_max_pages,
                optimize_dpi=self.config.docling_optimize_dpi,
                optimize_jpeg_quality=self.config.docling_optimize_jpeg_quality,
            )

        # Duplicate detector (optional)
        self.duplicate_detector: Any = None
        if HAS_DUPLICATE_DETECTOR:
            try:
                self.duplicate_detector = _DuplicateDetector()
            except Exception:
                pass  # Qdrant olmayabilir

        # Ensure directories exist
        INTAKE_DIR.mkdir(exist_ok=True)
        REJECTED_DIR.mkdir(exist_ok=True)
        REVIEW_DIR.mkdir(exist_ok=True)
        REPORTS_DIR.mkdir(exist_ok=True)

    def get_pending_files(self, recursive: bool = True) -> List[Path]:
        """_intake/ klasöründeki işlenecek dosyaları listele."""
        if not INTAKE_DIR.exists():
            return []

        files = []

        if recursive:
            # Alt klasörler dahil tara
            for item in INTAKE_DIR.rglob("*"):
                if item.is_file() and not item.name.startswith("."):
                    files.append(item)
        else:
            # Sadece kök dizin
            for item in INTAKE_DIR.iterdir():
                if item.is_file() and not item.name.startswith("."):
                    files.append(item)

        return sorted(files, key=lambda p: p.stat().st_mtime)

    def process_file(self, file_path: Path) -> ProcessingResult:
        """Tek dosyayı işle."""
        result = ProcessingResult(
            original_path=file_path, status=ProcessingStatus.ERROR
        )
        scan_result: Optional[ScanResult] = None

        try:
            hint = self.hint_loader.load_hint(file_path)

            # === Step 1: Technical Scan ===
            if self.verbose:
                console.print(f"  [dim]1/6 Teknik tarama...[/dim]")

            try:
                scan_result = self.scanner.scan(str(file_path))
            except TechnicalError as e:
                # Teknik hata - rejected'a taşı
                result.status = ProcessingStatus.REJECTED
                result.error_message = f"Teknik hata: {str(e)}"

                if not self.dry_run:
                    self._move_to_rejected(file_path, "technical_error")
                    # Report technical rejection
                    self.report_writer.add_technical_rejection(
                        file_path=str(file_path),
                        error_type=type(e).__name__,
                        error_message=str(e),
                    )

                return result

            # === Step 1.5: Docling PDF optimization + extraction ===
            docling_extraction = None
            docling_mode = self.config.docling_mode
            if self.docling_gateway and scan_result.extension.lower() == ".pdf":
                if self.verbose:
                    console.print("  [dim]1.5/6 Docling optimize/extract...[/dim]")

                optimization = self.docling_gateway.maybe_optimize_scanned_pdf(
                    str(file_path), scan_result
                )

                if optimization.optimized:
                    if self.verbose:
                        console.print(
                            f"    [green]PDF optimize:[/green] {optimization.old_size_mb:.1f}MB -> "
                            f"{optimization.new_size_mb:.1f}MB ({optimization.saved_percent:.0f}% kazanç)"
                        )
                    # Dosya boyutu/katman bilgisi güncellensin
                    try:
                        scan_result = self.scanner.scan(str(file_path))
                    except TechnicalError:
                        pass

                docling_extraction = self.docling_gateway.extract_pdf(str(file_path))
                result.docling_info = {
                    "mode": docling_mode,
                    "extraction_success": docling_extraction.success,
                    "extracted_chars": docling_extraction.extracted_chars,
                    "quality_score": docling_extraction.quality_score,
                    "reason": docling_extraction.reason,
                    "optimized": optimization.optimized,
                    "old_size_mb": optimization.old_size_mb,
                    "new_size_mb": optimization.new_size_mb,
                    "saved_percent": optimization.saved_percent,
                }

            # === Step 2: Content Preparation ===
            if self.verbose:
                console.print(f"  [dim]2/6 İçerik hazırlama...[/dim]")

            prepared = self.preparer.prepare(scan_result)

            # Docling extraction başarılıysa vision yerine text kullan.
            if (
                docling_extraction
                and docling_extraction.success
                and docling_mode in ("enforce", "shadow")
                and prepared.mode.value != "text"
            ):
                prepared.mode = ContentMode.TEXT
                prepared.text_content = docling_extraction.text[:3000]
                prepared.pages_sampled = min(scan_result.page_count or 1, 2)
                prepared.images_base64 = []
                prepared.note = "Docling extraction ile text mode'a geçirildi"

            # Enforce modunda extraction yetersizse pahalı vision çağrısını atlayıp review'a al.
            if (
                docling_extraction
                and not docling_extraction.success
                and docling_mode == "enforce"
                and prepared.mode.value == "vision"
            ):
                result.status = ProcessingStatus.REVIEW
                result.error_message = "Docling extraction yetersiz; yüksek maliyetli vision çağrısı atlandı"
                if not self.dry_run:
                    self._move_to_review(file_path)
                    self.report_writer.add_file_result(
                        scan_result=scan_result,
                        analysis_result=None,
                        final_decision="REVIEW",
                        new_filename=None,
                        final_path=None,
                        analysis_mode="docling_guardrail",
                        error=result.error_message,
                        docling_info=result.docling_info,
                    )
                return result

            # === Step 3: LLM Analysis ===
            if self.verbose:
                console.print(f"  [dim]3/6 LLM analizi...[/dim]")

            analysis = self.analyzer.analyze(scan_result, prepared, hint=hint)
            result.analysis = analysis

            # Check if rejected by LLM
            if analysis.decision == "REJECTED":
                result.status = ProcessingStatus.REJECTED
                result.error_message = f"LLM red: {analysis.decision_reason}"

                if not self.dry_run:
                    self._move_to_rejected(file_path, "llm_rejected")
                    self.report_writer.add_file_result(
                        scan_result=scan_result,
                        analysis_result=analysis,
                        final_decision="REJECTED",
                        new_filename=None,
                        final_path=None,
                        analysis_mode=prepared.mode.value,
                        error=result.error_message,
                        docling_info=result.docling_info,
                    )

                return result

            # === Step 4: Duplicate Check ===
            if self.verbose:
                console.print(f"  [dim]4/6 Duplicate kontrolü...[/dim]")

            if (
                self.duplicate_detector
                and prepared.text_content
                and HAS_DUPLICATE_DETECTOR
            ):
                dup_result = self.duplicate_detector.check_duplicate(
                    text=prepared.text_content[:5000],  # İlk 5000 karakter
                    semester=analysis.semester_guess,
                    course=analysis.course_name,
                )

                if dup_result.decision == _DuplicateDecision.DUPLICATE:
                    result.status = ProcessingStatus.REJECTED
                    result.error_message = f"Duplicate: {dup_result.reason}"
                    result.duplicate_info = {
                        "similarity": dup_result.similarity,
                        "similar_docs": dup_result.similar_documents,
                    }

                    if not self.dry_run:
                        self._move_to_rejected(file_path, "duplicate")
                        self.report_writer.add_file_result(
                            scan_result=scan_result,
                            analysis_result=analysis,
                            final_decision="REJECTED",
                            new_filename=None,
                            final_path=None,
                            duplicate_result=result.duplicate_info,
                            analysis_mode=prepared.mode.value,
                            error=result.error_message,
                            docling_info=result.docling_info,
                        )

                    return result

                elif dup_result.decision == _DuplicateDecision.SIMILAR:
                    # Manuel inceleme gerekiyor
                    result.status = ProcessingStatus.REVIEW
                    result.error_message = f"Benzer dosya mevcut: {dup_result.reason}"
                    result.duplicate_info = {
                        "similarity": dup_result.similarity,
                        "similar_docs": dup_result.similar_documents,
                    }

                    if not self.dry_run:
                        self._move_to_review(file_path)
                        self.report_writer.add_file_result(
                            scan_result=scan_result,
                            analysis_result=analysis,
                            final_decision="REVIEW",
                            new_filename=None,
                            final_path=None,
                            duplicate_result=result.duplicate_info,
                            analysis_mode=prepared.mode.value,
                            error=result.error_message,
                            docling_info=result.docling_info,
                        )

                    return result

            # Check if LLM says REVIEW
            if analysis.decision == "REVIEW":
                result.status = ProcessingStatus.REVIEW
                result.error_message = f"Manuel inceleme: {analysis.decision_reason}"

                if not self.dry_run:
                    self._move_to_review(file_path)
                    self.report_writer.add_file_result(
                        scan_result=scan_result,
                        analysis_result=analysis,
                        final_decision="REVIEW",
                        new_filename=None,
                        final_path=None,
                        analysis_mode=prepared.mode.value,
                        error=result.error_message,
                        docling_info=result.docling_info,
                    )

                return result

            # === Step 5: Filename Generation ===
            if self.verbose:
                console.print(f"  [dim]5/6 Dosya adı üretimi...[/dim]")

            # Geçici hedef klasör (path resolver sonra kesin belirleyecek)
            temp_target_dir = str(
                REPO_ROOT / analysis.semester_guess / analysis.course_name
            )

            generated_name = self.filename_gen.generate(
                analysis=analysis,
                extension=file_path.suffix.lower(),
                target_dir=temp_target_dir,
            )
            result.generated_filename = generated_name

            # === Step 6: Path Resolution ===
            if self.verbose:
                console.print(f"  [dim]6/6 Hedef klasör belirleme...[/dim]")

            # Intake folder - dosyanın bulunduğu klasör (dönem tespiti için)
            intake_folder = str(file_path.parent)

            try:
                target_dir, target_path_str = self.path_resolver.resolve(
                    analysis=analysis,
                    intake_folder=intake_folder,
                    new_filename=generated_name,
                    hint=hint,
                )
                target_path = Path(target_path_str)
            except Exception as e:
                # Path resolve başarısız - review'a gönder
                result.status = ProcessingStatus.REVIEW
                result.error_message = f"Yol belirlenemedi: {str(e)}"

                if not self.dry_run:
                    self._move_to_review(file_path)
                    self.report_writer.add_file_result(
                        scan_result=scan_result,
                        analysis_result=analysis,
                        final_decision="REVIEW",
                        new_filename=generated_name,
                        final_path=None,
                        analysis_mode=prepared.mode.value,
                        error=result.error_message,
                        docling_info=result.docling_info,
                    )

                return result

            # Ensure unique filename
            target_path = self._ensure_unique_path(target_path)
            result.final_path = target_path

            # === Move File ===
            if not self.dry_run:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(target_path))

                # Add to vector DB if available
                if (
                    self.duplicate_detector
                    and prepared.text_content
                    and HAS_DUPLICATE_DETECTOR
                ):
                    self.duplicate_detector.add_document(
                        text=prepared.text_content[:5000],
                        metadata={
                            "semester": analysis.semester_guess,
                            "course": analysis.course_name,
                            "filename": generated_name,
                            "path": str(target_path),
                            "material_type": analysis.material_type,
                        },
                    )

                # Add to report
                self.report_writer.add_file_result(
                    scan_result=scan_result,
                    analysis_result=analysis,
                    final_decision="ACCEPTED",
                    new_filename=generated_name,
                    final_path=str(target_path),
                    analysis_mode=prepared.mode.value,
                    docling_info=result.docling_info,
                )

            result.status = ProcessingStatus.SUCCESS
            return result

        except Exception as e:
            result.status = ProcessingStatus.ERROR
            result.error_message = str(e)
            if not self.dry_run and scan_result is not None:
                try:
                    self.report_writer.add_file_result(
                        scan_result=scan_result,
                        analysis_result=result.analysis,
                        final_decision="ERROR",
                        new_filename=result.generated_filename,
                        final_path=str(result.final_path)
                        if result.final_path
                        else None,
                        analysis_mode=(
                            "text"
                            if result.analysis and result.analysis.model_used
                            else "unknown"
                        ),
                        error=result.error_message,
                        docling_info=result.docling_info,
                    )
                except Exception:
                    pass
            return result

    def _move_to_rejected(self, file_path: Path, reason: str) -> Path:
        """Dosyayı _rejected/ klasörüne taşı."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{reason}_{timestamp}_{file_path.name}"
        target = REJECTED_DIR / new_name
        shutil.move(str(file_path), str(target))
        return target

    def _move_to_review(self, file_path: Path) -> Path:
        """Dosyayı _review/ klasörüne taşı."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"review_{timestamp}_{file_path.name}"
        target = REVIEW_DIR / new_name
        shutil.move(str(file_path), str(target))
        return target

    def _ensure_unique_path(self, path: Path) -> Path:
        """Eğer dosya varsa version numarası ekle."""
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        parent = path.parent

        # _v{n} pattern'i var mı kontrol et
        import re

        version_match = re.search(r"_v(\d+)$", stem)

        if version_match:
            base_stem = stem[: version_match.start()]
            current_version = int(version_match.group(1))
        else:
            base_stem = stem
            current_version = 1

        # Yeni version bul
        while True:
            current_version += 1
            new_path = parent / f"{base_stem}_v{current_version}{suffix}"
            if not new_path.exists():
                return new_path

    def run_batch(self, files: Optional[List[Path]] = None) -> BatchResult:
        """Birden fazla dosyayı işle."""
        batch = BatchResult()

        if files is None:
            files = self.get_pending_files()

        # Start report run
        self.report_writer.start_run()

        for file_path in files:
            result = self.process_file(file_path)
            batch.processed.append(result)

        batch.end_time = datetime.now()

        # Finish report
        if batch.processed:
            duration = (batch.end_time - batch.start_time).total_seconds()
            self.report_writer.finish_run(
                total_files=len(batch.processed),
                duration_seconds=duration,
            )

        return batch


# === CLI Commands ===


@app.command()
def run(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Sadece analiz, dosya taşıma"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Detaylı çıktı"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Tek dosya işle"),
    skip_duplicates: bool = typer.Option(
        True, "--skip-duplicates/--no-skip-duplicates", help="Duplicate kontrolü"
    ),
):
    """
    Intake pipeline'ı çalıştır.

    _intake/ klasöründeki tüm dosyaları işler veya --file ile
    tek dosya belirtebilirsiniz.
    """
    agent = IntakeAgent(
        dry_run=dry_run,
        verbose=verbose,
        skip_duplicates=skip_duplicates,
    )

    # API key kontrolü
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]ANTHROPIC_API_KEY environment variable gerekli![/red]")
        console.print("  export ANTHROPIC_API_KEY=sk-ant-...")
        raise typer.Exit(1)

    # Dosya listesi
    if file:
        if not file.exists():
            console.print(f"[red]Dosya bulunamadı: {file}[/red]")
            raise typer.Exit(1)
        files = [file]
    else:
        files = agent.get_pending_files()

    if not files:
        console.print("[yellow]İşlenecek dosya yok.[/yellow]")
        console.print(f"  Dosyaları {INTAKE_DIR}/ klasörüne koyun.")
        raise typer.Exit(0)

    # Header
    mode_str = "[yellow](DRY-RUN)[/yellow]" if dry_run else ""
    console.print(
        Panel(
            f"[bold]ktunDepo Intake Agent[/bold] {mode_str}\n"
            f"İşlenecek dosya sayısı: {len(files)}",
            title="Toplu Materyal Alımı",
        )
    )

    # Start report
    agent.report_writer.start_run()

    # Process files
    batch = BatchResult()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for i, f in enumerate(files, 1):
            task = progress.add_task(f"[{i}/{len(files)}] {f.name}", total=None)

            result = agent.process_file(f)
            batch.processed.append(result)

            # Status emoji
            status_map = {
                ProcessingStatus.SUCCESS: "[green]✓[/green]",
                ProcessingStatus.REJECTED: "[red]✗[/red]",
                ProcessingStatus.REVIEW: "[yellow]?[/yellow]",
                ProcessingStatus.ERROR: "[red]![/red]",
                ProcessingStatus.SKIPPED: "[dim]-[/dim]",
            }
            status_str = status_map.get(result.status, "???")

            progress.remove_task(task)

            # Output
            if result.status == ProcessingStatus.SUCCESS:
                console.print(f"  {status_str} {f.name}")
                if result.final_path:
                    rel_path = result.final_path.relative_to(REPO_ROOT)
                    console.print(f"       -> {rel_path}")
            else:
                console.print(f"  {status_str} {f.name}")
                if result.error_message:
                    console.print(f"       [dim]{result.error_message[:80]}[/dim]")

    batch.end_time = datetime.now()

    # Finish report
    duration = (batch.end_time - batch.start_time).total_seconds()
    agent.report_writer.finish_run(
        total_files=len(batch.processed),
        duration_seconds=duration,
    )

    # Summary
    console.print()
    console.print(
        Panel(
            f"[green]Başarılı:[/green] {batch.success_count}  "
            f"[red]Reddedilen:[/red] {batch.rejected_count}  "
            f"[yellow]İnceleme:[/yellow] {batch.review_count}  "
            f"[red]Hata:[/red] {batch.error_count}",
            title="Özet",
        )
    )


@app.command()
def status():
    """Kuyruk durumunu göster."""
    agent = IntakeAgent(dry_run=True)

    files = agent.get_pending_files()

    if not files:
        console.print("[green]Kuyruk boş.[/green]")
        return

    table = Table(title=f"Bekleyen Dosyalar ({len(files)})")
    table.add_column("Dosya", style="cyan")
    table.add_column("Boyut", justify="right")
    table.add_column("Tarih")

    for f in files:
        size = f.stat().st_size
        size_str = (
            f"{size / 1024:.1f} KB"
            if size < 1024 * 1024
            else f"{size / 1024 / 1024:.1f} MB"
        )
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        table.add_row(f.name, size_str, mtime)

    console.print(table)

    # Rejected/Review counts
    rejected_count = len(list(REJECTED_DIR.glob("*"))) if REJECTED_DIR.exists() else 0
    review_count = len(list(REVIEW_DIR.glob("*"))) if REVIEW_DIR.exists() else 0

    if rejected_count or review_count:
        console.print()
        console.print(f"[red]Reddedilen:[/red] {rejected_count} dosya (_rejected/)")
        console.print(
            f"[yellow]İnceleme bekleyen:[/yellow] {review_count} dosya (_review/)"
        )


@app.command()
def report(
    last: int = typer.Option(1, "--last", "-l", help="Son N raporu göster"),
):
    """Son raporları göster."""
    if not REPORTS_DIR.exists():
        console.print("[yellow]Henüz rapor yok.[/yellow]")
        return

    # Find summary.json files in subdirectories
    reports = []
    for run_dir in REPORTS_DIR.iterdir():
        if run_dir.is_dir():
            summary = run_dir / "summary.json"
            if summary.exists():
                reports.append(summary)

    reports = sorted(reports, key=lambda p: p.stat().st_mtime, reverse=True)

    if not reports:
        console.print("[yellow]Henüz rapor yok.[/yellow]")
        return

    import json

    for report_path in reports[:last]:
        try:
            with open(report_path) as f:
                data = json.load(f)

            stats = data.get("statistics", {})
            tokens = data.get("token_usage", {})

            console.print(
                Panel(
                    f"[bold]{data.get('run_id', 'N/A')}[/bold]\n"
                    f"Süre: {data.get('duration_seconds', 0):.1f} saniye\n"
                    f"Toplam: {data.get('total_files', 0)} dosya\n"
                    f"Başarılı: {stats.get('accepted', 0)}\n"
                    f"Reddedilen: {stats.get('rejected', 0)}\n"
                    f"İnceleme: {stats.get('review', 0)}\n"
                    f"Token: {tokens.get('input', 0)} in / {tokens.get('output', 0)} out",
                    title="Rapor",
                )
            )
        except Exception as e:
            console.print(f"[red]Rapor okunamadı: {e}[/red]")


@app.command()
def clean(
    rejected: bool = typer.Option(False, "--rejected", "-r", help="_rejected/ temizle"),
    review: bool = typer.Option(False, "--review", help="_review/ temizle"),
    force: bool = typer.Option(False, "--force", "-f", help="Onay sorma"),
):
    """Reddedilen veya inceleme dosyalarını temizle."""
    targets = []

    if rejected and REJECTED_DIR.exists():
        targets.append(("_rejected", REJECTED_DIR))
    if review and REVIEW_DIR.exists():
        targets.append(("_review", REVIEW_DIR))

    if not targets:
        console.print("[yellow]Temizlenecek klasör belirtilmedi.[/yellow]")
        console.print("  --rejected veya --review kullanın.")
        return

    for name, path in targets:
        files = list(path.glob("*"))
        if not files:
            console.print(f"[dim]{name}/ zaten boş.[/dim]")
            continue

        if not force:
            confirm = typer.confirm(
                f"{name}/ klasöründeki {len(files)} dosya silinsin mi?"
            )
            if not confirm:
                continue

        for f in files:
            f.unlink()

        console.print(
            f"[green]{name}/ temizlendi ({len(files)} dosya silindi).[/green]"
        )


if __name__ == "__main__":
    app()
