import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class IntakeHint:
    """_intake klasörlerine konulan HINT.json verisi."""
    semester: Optional[str] = None
    course: Optional[str] = None


class HintLoader:
    """Klasör hiyerarşisinde HINT.json arar ve yükler."""

    def __init__(self, intake_root: str):
        self.intake_root = Path(intake_root)

    def load_hint(self, file_path: Path) -> Optional[IntakeHint]:
        """
        Dosyanın bulunduğu klasörden başlayarak yukarı doğru HINT.json arar.
        intake_root'a kadar çıkar.
        """
        current_dir = file_path if file_path.is_dir() else file_path.parent

        while current_dir != self.intake_root.parent:  # root'un dışına çıkma
            hint_file = current_dir / "HINT.json"
            if hint_file.exists():
                try:
                    with open(hint_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if isinstance(data, dict):
                        return IntakeHint(
                            semester=data.get("semester"),
                            course=data.get("course")
                        )
                except Exception as e:
                    print(f"HINT.json okuma hatası ({hint_file}): {e}")
                    pass
            
            if current_dir == self.intake_root:
                break
                
            current_dir = current_dir.parent

        return None
