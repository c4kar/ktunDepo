from pathlib import Path
from agent.models import ProcessingContext, UnifiedProcessingResult

def test_processing_context_instantiation():
    path = Path("dummy.pdf")
    ctx = ProcessingContext(file_path=path, source="telegram")
    
    # Assert explicitly passed
    assert ctx.file_path == path
    assert ctx.source == "telegram"
    
    # Assert defaults
    assert ctx.metadata == {}
    assert ctx.hint is None
    assert ctx.dry_run is False

def test_unified_processing_result_instantiation():
    path = Path("out.pdf")
    res = UnifiedProcessingResult(success=True, decision="ACCEPTED", final_path=path)
    
    # Assert explicitly passed
    assert res.success is True
    assert res.decision == "ACCEPTED"
    assert res.final_path == path
    
    # Assert defaults
    assert res.reason == ""
    assert res.tokens_used == 0
    assert res.error_message is None
