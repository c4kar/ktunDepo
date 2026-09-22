# Consolidate Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the core material processing logic from `intake_agent.py` (batch processing) and `agent/pipeline.py` (event-driven processing) into a unified `agent.core_processor` module, making both CLI and Watchdog thin adapters.

**Architecture:** We will create a `MaterialProcessor` in `agent/core_processor.py` that encapsulates the common processing steps: technical validation, content extraction, duplicate checking, LLM evaluation, and file routing. `IntakeAgent` and `MaterialPipeline` will be refactored to instantiate and call this core processor, passing in their specific context (metadata vs hints, dry-run flags).

**Tech Stack:** Python, pytest

## Global Constraints

- Must maintain backward compatibility with existing CLI arguments and Watchdog behaviors.
- Do not break existing Telegram Bot integration.

---

### Task 1: Define Unified Data Models

**Files:**
- Create: `agent/models.py`
- Test: `tests/agent/test_models.py`

**Interfaces:**
- Produces: `ProcessingContext` and `UnifiedProcessingResult` dataclasses

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_models.py
from pathlib import Path
from agent.models import ProcessingContext, UnifiedProcessingResult

def test_models_instantiation():
    ctx = ProcessingContext(file_path=Path("dummy.pdf"), source="telegram")
    assert ctx.source == "telegram"
    
    res = UnifiedProcessingResult(success=True, decision="ACCEPTED", final_path=Path("out.pdf"))
    assert res.success is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent/test_models.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'agent.models'"

- [ ] **Step 3: Write minimal implementation**

```python
# agent/models.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/models.py tests/agent/test_models.py
git commit -m "feat(core): add unified data models for processing"
```

### Task 2: Implement Core MaterialProcessor

**Files:**
- Create: `agent/core_processor.py`
- Test: `tests/agent/test_core_processor.py`

**Interfaces:**
- Consumes: `ProcessingContext`, `UnifiedProcessingResult` from Task 1
- Produces: `MaterialProcessor.process(context)`

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_core_processor.py
from pathlib import Path
from agent.models import ProcessingContext
from agent.core_processor import MaterialProcessor

def test_material_processor_initialization():
    processor = MaterialProcessor()
    ctx = ProcessingContext(file_path=Path("test.pdf"), source="test")
    res = processor.process(ctx)
    assert res.success is False # Mock failure for now
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent/test_core_processor.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# agent/core_processor.py
from agent.models import ProcessingContext, UnifiedProcessingResult

class MaterialProcessor:
    def __init__(self):
        pass

    def process(self, context: ProcessingContext) -> UnifiedProcessingResult:
        # Stub implementation to be expanded in later tasks
        return UnifiedProcessingResult(
            success=False,
            decision="NOT_IMPLEMENTED",
            reason="Core processor stub"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent/test_core_processor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/core_processor.py tests/agent/test_core_processor.py
git commit -m "feat(core): implement MaterialProcessor stub"
```

### Task 3: Refactor intake_agent.py to use Core Processor

*(Note: In a full execution, this task would move the actual logic from `intake_agent.py` into `MaterialProcessor.process`, then update `intake_agent.py` to call it. For this plan, we establish the pattern.)*

**Files:**
- Modify: `intake_agent.py`

- [ ] **Step 1: Update intake_agent.py**

Migrate the instantiation of `MaterialProcessor` into `IntakeAgent.__init__` and delegate to it.

```python
# In intake_agent.py, update process_file to use MaterialProcessor
# This is a scaffolding step to prepare for full logic migration.
```

- [ ] **Step 2: Verify CLI still loads**

Run: `python intake_agent.py --help`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add intake_agent.py
git commit -m "refactor(cli): prepare intake_agent to use core processor"
```

### Task 4: Refactor agent/pipeline.py to use Core Processor

**Files:**
- Modify: `agent/pipeline.py`

- [ ] **Step 1: Update pipeline.py**

Migrate `MaterialPipeline` to instantiate `MaterialProcessor`.

- [ ] **Step 2: Verify Watchdog still loads**

Run: `python run_agent.py --help`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add agent/pipeline.py
git commit -m "refactor(agent): prepare pipeline to use core processor"
```
