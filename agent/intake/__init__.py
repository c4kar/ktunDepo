"""
ktunDepo Intake Agent — Toplu Materyal Alım Sistemi

_intake/ klasörüne yığılan materyalleri analiz edip
uygun klasörlere taşıyan LLM-first pipeline.

Temel Felsefe: LLM birincil yargıçtır. Python sadece
teknik olarak bozuk dosyaları (açılamayan, 0 byte) eliyebilir.
"""

from agent.intake.file_scanner import FileScanner, ScanResult, TechnicalError
from agent.intake.content_preparer import ContentPreparer, PreparedContent
from agent.intake.llm_analyzer import LLMAnalyzer, AnalysisResult
from agent.intake.filename_generator import FilenameGenerator
from agent.intake.path_resolver import PathResolver
from agent.intake.report_writer import ReportWriter
from agent.intake.docling_gateway import (
    DoclingGateway,
    DoclingExtractionResult,
    OptimizationResult,
)

__all__ = [
    "FileScanner",
    "ScanResult",
    "TechnicalError",
    "ContentPreparer",
    "PreparedContent",
    "LLMAnalyzer",
    "AnalysisResult",
    "FilenameGenerator",
    "PathResolver",
    "ReportWriter",
    "DoclingGateway",
    "DoclingExtractionResult",
    "OptimizationResult",
]
