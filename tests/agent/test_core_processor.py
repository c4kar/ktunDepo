from pathlib import Path
from agent.models import ProcessingContext
from agent.core_processor import MaterialProcessor

def test_material_processor_initialization():
    processor = MaterialProcessor()
    ctx = ProcessingContext(file_path=Path("test.pdf"), source="test")
    res = processor.process(ctx)
    assert res.success is False # Mock failure for now
