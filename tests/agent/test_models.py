from pathlib import Path
from agent.models import ProcessingContext, UnifiedProcessingResult

def test_models_instantiation():
    ctx = ProcessingContext(file_path=Path("dummy.pdf"), source="telegram")
    assert ctx.source == "telegram"
    
    res = UnifiedProcessingResult(success=True, decision="ACCEPTED", final_path=Path("out.pdf"))
    assert res.success is True
