from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any

@dataclass
class ProcessingContext:
    file_path: Path
    source: str # e.g., 'cli', 'telegram'
    metadata: Dict[str, Any] = field(default_factory=dict)
    hint: Optional[Any] = None
    dry_run: bool = False

@dataclass
class UnifiedProcessingResult:
    success: bool
    decision: str
    final_path: Optional[Path] = None
    reason: str = ""
    tokens_used: int = 0
    error_message: Optional[str] = None
