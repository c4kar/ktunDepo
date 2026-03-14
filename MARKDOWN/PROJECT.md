# ktunDepo — Project Documentation

> **Comprehensive overview of the ktunDepo educational material repository system**

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [System Components](#system-components)
- [Pipelines](#pipelines)
- [Directory Structure](#directory-structure)
- [Configuration](#configuration)
- [Development Guide](#development-guide)
- [Deployment](#deployment)

---

## Overview

**ktunDepo** is an intelligent, event-driven educational material repository system for Konya Technical University's Electrical-Electronics Engineering (EEM) program. It automates the ingestion, quality control, organization, and distribution of course materials (lecture notes, exams, presentations, etc.) using AI agents.

### Key Features

- **Dual Intake System**: Telegram bot + bulk folder ingestion
- **LLM-First Quality Control**: Claude Sonnet for content analysis
- **Vector-Based Duplicate Detection**: Qdrant + sentence-transformers
- **Event-Driven Architecture**: Only runs when needed (file uploads, scheduled tasks)
- **Automatic OCR**: Converts scanned documents to searchable Markdown
- **Git-Based Version Control**: Auto-commits accepted materials
- **State Machine Management**: SLEEPING → ACTIVE → MAINTENANCE modes

### Tech Stack

| Component | Technology |
|-----------|-----------|
| **AI Orchestration** | LangGraph (state machine) |
| **LLM Provider** | Anthropic Claude (Sonnet 4, Haiku 3.5) |
| **Vector DB** | Qdrant (local instance) |
| **Embeddings** | multilingual-e5-large (sentence-transformers) |
| **OCR** | Docling (IBM) + Claude for formatting |
| **Bot Framework** | python-telegram-bot |
| **File Monitoring** | watchdog |
| **Version Control** | GitPython |
| **Package Manager** | uv (modern pip alternative) |

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     ktunDepo System Architecture                 │
└─────────────────────────────────────────────────────────────────┘

Input Layer:
┌──────────────┐         ┌──────────────┐
│ Telegram Bot │────────▶│  _incoming/  │
│  (Upload)    │         │   (buffer)   │
└──────────────┘         └──────────────┘
                                │
┌──────────────┐                │
│  _intake/    │◀───────────────┘
│  (bulk)      │         watchdog triggers
└──────────────┘

Processing Layer:
┌─────────────────────────────────────────────────────┐
│            Material Pipeline (LangGraph)             │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐   │
│  │ Scan   │─▶│Quality │─▶│Duplicate│─▶│  LLM   │   │
│  │(tech)  │  │(heur.) │  │ (Qdrant)│  │(Claude)│   │
│  └────────┘  └────────┘  └────────┘  └────────┘   │
│       │                                     │        │
│       ▼                                     ▼        │
│  ┌────────┐                           ┌────────┐   │
│  │Rejected│                           │  OCR   │   │
│  │        │                           │(needed)│   │
│  └────────┘                           └────────┘   │
└─────────────────────────────────────────────────────┘

Output Layer:
┌────────────┐  ┌────────────┐  ┌────────────┐
│ _rejected/ │  │  _review/  │  │  EEM-X/    │
│  (failed)  │  │  (manual)  │  │ (courses)  │
└────────────┘  └────────────┘  └────────────┘
                                      │
                                      ▼
                                ┌────────────┐
                                │ Git Commit │
                                │    Push    │
                                └────────────┘
```

### Agent State Machine

```
      ┌──────────────┐
      │   SLEEPING   │ ◀─── Default mode (no resources)
      └──────────────┘
            │ ▲
    file    │ │ queue
    event   │ │ empty
            ▼ │
      ┌──────────────┐
      │    ACTIVE    │ ◀─── Processing materials
      └──────────────┘
            │
       git  │ critical
      error │ error
            ▼
      ┌──────────────┐
      │ MAINTENANCE  │ ◀─── Manual intervention required
      └──────────────┘
            │
    admin   │
   /resume  │
            ▼
      Health Check ──▶ ACTIVE
```

---

## System Components

### 1. Telegram Bot (`bot/`)

**Purpose**: User interface for material uploads

**Components**:
- `telegram_bot.py` - Main bot instance
- `handlers/` - Command and callback handlers

**Features**:
- `/start` - Welcome message
- `/upload` - Material submission
- `/status` - Agent status
- `/stats` - Repository statistics
- `/resume` - Admin recovery command

**Upload Flow**:
```
User uploads file
    ↓
Bot receives document
    ↓
Rate limit check (10/day per user)
    ↓
Move to _incoming/ with metadata.json
    ↓
Trigger agent wake-up
```

### 2. Legacy Pipeline (`agent/pipeline.py`)

**Purpose**: Original event-driven processing system (Telegram path)

**State Machine**: LangGraph-based orchestrator
- Monitors `_incoming/` with watchdog
- Processes files through quality → duplicate → LLM → OCR chain
- Moves to `EEM-X/Course/` or rejection folders

**Decision Flow**:
```
Quality Score < 30 ────────────▶ REJECT (_rejected/)
Quality Score 30-60 ───▶ LLM ──▶ REVIEW (_review/)
Quality Score > 60 ────────────▶ ACCEPT (EEM-X/)
```

### 3. Intake Agent (`intake_agent.py` + `agent/intake/`)

**Purpose**: **NEW** bulk material ingestion system (LLM-first approach)

**Philosophy**: 
- LLM is the primary judge
- Python only filters technically broken files (corrupted, 0 bytes, unsupported formats)
- Page count, text density, etc. are NOT rejection criteria

**Modules**:

| Module | Purpose |
|--------|---------|
| `file_scanner.py` (298 lines) | Technical scanning - only rejects truly broken files |
| `content_preparer.py` (271 lines) | Prepares text/vision/metadata content for LLM |
| `hint_loader.py` | Loads `HINT.json` manual overrides for target paths |
| `llm_analyzer.py` (365 lines) | Claude API integration with vision support |
| `filename_generator.py` (141 lines) | Standard filename: `{type}_{topic}_{year}_v{n}.ext` |
| `path_resolver.py` (224 lines) | Target path resolution with fuzzy matching and hint overrides |
| `report_writer.py` (297 lines) | JSON reports |

**HINT.json System**:
If the user wants to force a specific semester and course for a batch of files, they can place a `HINT.json` file in the folder (e.g. `_intake/devre_analizi_2/HINT.json`). This bypasses the LLM's fuzzy matching and ensures 100% accurate path resolution:
```json
{
  "semester": "EEM-2",
  "course": "devre-analizi-2"
}
```

**CLI Commands** (`intake_agent.py` - 706 lines):
```bash
# Process all files in _intake/
python intake_agent.py run

# Dry-run (analysis only, no file moves)
python intake_agent.py run --dry-run

# Process single file
python intake_agent.py run --file material.pdf

# Show queue status
python intake_agent.py status

# View last report
python intake_agent.py report

# Clean rejected/review folders
python intake_agent.py clean --rejected --force
```

**Intake Pipeline** (8 steps):
```
1. Technical Scan ──▶ Corrupted? ──▶ _rejected/
                         │
                         ▼ OK
2. Content Prep  ──▶ Extract text/images (and load HINT.json context if exists)
                         │
                         ▼
3. LLM Analysis  ──▶ Claude Sonnet (vision if needed, uses HINT constraints)
                         │
                         ▼
4. Duplicate     ──▶ Qdrant similarity check
   Check                 │
                         ▼
5. Filename Gen  ──▶ sinav_vektorler_2022_v1.pdf
                         │
                         ▼
6. Path Resolve  ──▶ EEM-2/Fizik/sinav_vektorler_2022_v1.pdf
                         │
                         ▼
7. File Move     ──▶ shutil.move() (or dry-run skip)
                         │
                         ▼
8. Report        ──▶ _reports/{run_id}/summary.json
```

**Intake vs Legacy Pipeline**:

| Feature | Legacy Pipeline | Intake Agent |
|---------|----------------|--------------|
| **Trigger** | Telegram bot uploads | Bulk folder drop |
| **Judge** | Heuristics → LLM fallback | LLM-first always |
| **Vision** | No | Yes (Claude Sonnet 4) |
| **Report** | State JSON | Detailed JSON reports |
| **Mode** | Event-driven (watchdog) | CLI batch processing |

### 4. Supporting Scripts (`scripts/`)

#### `quality_checker.py`
- **Heuristic quality scorer** (0-100 points)
- Checks: file size, page count, text density
- **ISSUE**: Line 166-173 incorrectly reject <2 pages (fixed in intake agent)

#### `duplicate_detector.py`
- **Vector similarity search** using Qdrant
- Embeds first 3 pages with multilingual-e5-large
- Decision thresholds:
  - `> 0.92` → DUPLICATE (reject)
  - `0.75-0.92` → SIMILAR (LLM review)
  - `< 0.75` → UNIQUE (accept)

#### `course_resolver.py`
- **Fuzzy matching** for course names (rapidfuzz)
- Maps "fizik" → "Fizik", "mek" → "Mühendislik Mekaniği"
- Threshold: 75% similarity

#### `git_manager.py`
- **Auto-commit** on material acceptance
- **Daily push** at 03:00 UTC
- **Maintenance detection** (merge conflicts, push failures)

#### `ocr_pipeline.py`
- **Docling** for OCR extraction
- **Claude Haiku** for Markdown formatting
- Triggered for scanned PDFs (no text layer)

### 5. State Management (`agent/state_manager.py`)

**Purpose**: Persistent agent state across restarts

**State File**: `agent/state.json`
```json
{
  "mode": "SLEEPING",
  "last_active": "2024-03-03T15:54:00Z",
  "maintenance_reason": null,
  "queue_size": 0,
  "total_processed_today": 42
}
```

**Modes**:
- `SLEEPING`: Idle, no resource usage
- `ACTIVE`: Processing materials
- `MAINTENANCE`: Admin intervention required (git conflicts, Qdrant down)

### 6. Configuration (`agent/config.yaml`)

**Key Settings**:
```yaml
quality:
  reject_threshold: 30
  llm_threshold: 60
  min_pages: 2

duplicate_detection:
  reject_similarity: 0.92
  warn_similarity: 0.75

ocr:
  engine: "docling"
  format_model: "anthropic/claude-3.5-sonnet-20241022"

llm:
  quality_model: "anthropic/claude-3-haiku-20240307"
  
git:
  auto_commit: true
  daily_push_time: "03:00"

telegram:
  daily_upload_limit: 10
```

---

## Pipelines

### Pipeline Comparison

| | Legacy Pipeline | Intake Agent |
|-|----------------|--------------|
| **Entry Point** | `_incoming/` (Telegram bot) | `_intake/` (manual drops) |
| **Orchestration** | LangGraph state machine | Typer CLI |
| **Quality Filter** | Heuristic → LLM (if 30-60) | LLM-first always |
| **Vision Support** | ❌ No | ✅ Yes (Claude Sonnet) |
| **Duplicate Check** | Qdrant vector search | Qdrant vector search |
| **OCR** | Docling + Claude | Docling + Claude |
| **Output** | `EEM-X/Course/` | `EEM-X/Course/` |
| **Report** | State JSON | Detailed JSON in `_reports/` |
| **Error Handling** | State machine → MAINTENANCE | Status codes + error messages |

### When to Use Which Pipeline

**Use Legacy Pipeline when**:
- Materials come via Telegram bot
- Need event-driven processing (watchdog)
- Want integrated state machine for recovery

**Use Intake Agent when**:
- Bulk folder drops (e.g., 50 PDFs from USB)
- Need vision analysis (scanned handwritten notes)
- Want detailed batch reports
- Prefer CLI over daemon

---

## Directory Structure

```
ktunDepo/
├── agent/                          # AI Agent System
│   ├── __init__.py
│   ├── config.yaml                 # Main configuration
│   ├── config_loader.py            # Config parser
│   ├── state.json                  # Persistent state
│   ├── state_manager.py            # State persistence
│   ├── pipeline.py                 # Legacy LangGraph orchestrator
│   ├── llm_evaluator.py            # Claude quality evaluator
│   ├── logging_config.py           # Logging setup
│   ├── intake/                     # NEW: Intake agent modules
│   │   ├── __init__.py
│   │   ├── file_scanner.py         # Technical file scanning
│   │   ├── content_preparer.py     # Content extraction
│   │   ├── hint_loader.py          # HINT.json metadata loader
│   │   ├── llm_analyzer.py         # Claude integration
│   │   ├── filename_generator.py   # Standard naming
│   │   ├── path_resolver.py        # Course/semester matching + hint overrides
│   │   └── report_writer.py        # JSON reports
│   ├── prompts/                    # LLM prompt templates
│   │   ├── quality_evaluation.md
│   │   └── markdown_format.md
│   └── logs/                       # Runtime logs
│
├── bot/                            # Telegram Bot
│   ├── __init__.py
│   ├── telegram_bot.py             # Main bot instance
│   └── handlers/                   # Command handlers
│
├── scripts/                        # Supporting Utilities
│   ├── quality_checker.py          # Heuristic quality scorer
│   ├── duplicate_detector.py       # Qdrant duplicate detection
│   ├── course_resolver.py          # Fuzzy course name matching
│   ├── git_manager.py              # Auto-commit/push
│   └── ocr_pipeline.py             # Docling OCR + Claude formatting
│
├── vector_db/                      # Qdrant database files
│
├── EEM-1/                          # Semester 1 courses
│   ├── Matematik/
│   ├── Fizik/
│   ├── Lineer Cebir/
│   ├── Kimya/
│   └── ...
│
├── EEM-2/                          # Semester 2 courses
│   ├── Devre Analizi/
│   ├── Elektronik/
│   ├── Lojik Devreler/
│   ├── Mühendislik Mekaniği/
│   └── ...
│
├── _incoming/                      # Telegram bot buffer (legacy)
├── _intake/                        # Bulk ingestion folder (NEW)
├── _rejected/                      # Failed quality checks
├── _review/                        # Manual review queue
├── _reports/                       # Intake agent reports (NEW)
│   └── intake_run_YYYYMMDD_HHMMSS/
│       ├── summary.json
│       ├── file1.json
│       └── ocr_queue.json
│
├── intake_agent.py                 # NEW: CLI for bulk ingestion
├── run_agent.py                    # Legacy pipeline runner
├── run_bot.py                      # Telegram bot runner
├── pyproject.toml                  # Python dependencies (uv)
├── .env                            # Environment variables
├── README.md                       # User documentation
├── PLAN.md                         # Bot improvement roadmap
└── PROJECT.md                      # This file
```

### Folder Purposes

| Folder | Purpose | Trigger | Retention |
|--------|---------|---------|-----------|
| `_incoming/` | Telegram bot buffer | Bot upload | Delete after processing |
| `_intake/` | Bulk ingestion | Manual drop | Delete after processing |
| `_rejected/` | Failed materials | Technical/quality fail | Manual cleanup |
| `_review/` | Manual review | LLM uncertain | Admin review |
| `_reports/` | Processing logs | Intake agent run | Keep for audit |
| `EEM-X/` | Final repository | Accepted materials | Git version control |

---

## Configuration

### Environment Variables (`.env`)

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...               # Claude API (intake agent)
OPENROUTER_API_KEY=sk-or-v1-...           # OpenRouter (legacy pipeline)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...      # Bot token

# Optional
QDRANT_HOST=localhost                      # Qdrant host
QDRANT_PORT=6333                           # Qdrant port
GIT_AUTO_COMMIT=true                       # Auto-commit on accept
LOG_LEVEL=INFO                             # DEBUG|INFO|WARNING|ERROR
```

### Config File (`agent/config.yaml`)

**Main sections**:
- `quality` - Heuristic thresholds
- `duplicate_detection` - Similarity thresholds
- `ocr` - OCR engine and formatting
- `llm` - Model selection (Haiku vs Sonnet)
- `git` - Auto-commit settings
- `telegram` - Rate limits
- `paths` - Directory paths
- `logging` - Log settings
- `maintenance` - Trigger conditions

**To modify behavior without code changes**, edit `config.yaml`.

---

## Development Guide

### Setup

```bash
# Clone repository
git clone https://github.com/c4kar/ktunDepo.git
cd ktunDepo

# Install dependencies with uv (modern pip alternative)
uv venv
source .venv/bin/activate
uv pip install -e .

# Or with pip
python -m venv venv
source venv/bin/activate
pip install -e .

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Start Qdrant (Docker)
docker run -d -p 6333:6333 qdrant/qdrant

# Run legacy pipeline
python run_agent.py

# Run Telegram bot (separate terminal)
python run_bot.py

# Run intake agent
python intake_agent.py run --dry-run
```

### Testing Workflows

#### Test Legacy Pipeline (Telegram Path)
```bash
# 1. Start agent
python run_agent.py

# 2. Upload via Telegram bot
# Bot moves file to _incoming/

# 3. Watch logs
tail -f agent/logs/agent_*.log

# 4. Check results
ls -la EEM-1/Fizik/
```

#### Test Intake Agent (Bulk Path)
```bash
# 1. Drop files into _intake/
cp ~/Downloads/*.pdf _intake/

# 2. Run intake agent (dry-run first)
python intake_agent.py run --dry-run -v

# 3. Check analysis
python intake_agent.py status
python intake_agent.py report

# 4. Run for real
python intake_agent.py run

# 5. Check reports
cat _reports/intake_run_*/summary.json
```

### Adding a New Course

1. Create folder: `EEM-X/Course Name/`
2. Add to `course_resolver.py` aliases (optional)
3. Update `config.yaml` if needed
4. Test fuzzy matching: `scripts/course_resolver.py --test "Course Name"`

### Debugging

**Check agent state**:
```bash
python run_agent.py --status
cat agent/state.json
```

**View logs**:
```bash
# All logs
tail -f agent/logs/*.log

# Pipeline only
tail -f agent/logs/pipeline.log

# Intake agent only
tail -f agent/logs/intake_agent.log
```

**Check Qdrant**:
```bash
# Collection stats
curl http://localhost:6333/collections/ktundepo_materials

# Search test
python -c "
from scripts.duplicate_detector import get_duplicate_detector
detector = get_duplicate_detector()
result = detector.check_duplicate('test text')
print(result)
"
```

---

## Deployment

### Production Checklist

- [ ] Set `ANTHROPIC_API_KEY` in production `.env`
- [ ] Set `OPENROUTER_API_KEY` for legacy pipeline
- [ ] Set `TELEGRAM_BOT_TOKEN`
- [ ] Configure `git` user and email
- [ ] Start Qdrant container with persistent volume
- [ ] Set `config.yaml` → `git.auto_commit: true`
- [ ] Set `config.yaml` → `git.daily_push_time: "03:00"`
- [ ] Configure systemd service for `run_agent.py`
- [ ] Configure systemd service for `run_bot.py`
- [ ] Set up log rotation
- [ ] Enable monitoring (disk usage, Qdrant status)

### Systemd Services

**`/etc/systemd/system/ktundepo-agent.service`**:
```ini
[Unit]
Description=ktunDepo Agent Pipeline
After=network.target

[Service]
Type=simple
User=ktundepo
WorkingDirectory=/home/ktundepo/ktunDepo
Environment="PATH=/home/ktundepo/ktunDepo/.venv/bin"
ExecStart=/home/ktundepo/ktunDepo/.venv/bin/python run_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/ktundepo-bot.service`**:
```ini
[Unit]
Description=ktunDepo Telegram Bot
After=network.target

[Service]
Type=simple
User=ktundepo
WorkingDirectory=/home/ktundepo/ktunDepo
Environment="PATH=/home/ktundepo/ktunDepo/.venv/bin"
ExecStart=/home/ktundepo/ktunDepo/.venv/bin/python run_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Monitoring

**Health check script** (`scripts/health_check.sh`):
```bash
#!/bin/bash
# Check agent state
STATE=$(python -c "from agent.state_manager import get_state_manager; print(get_state_manager().get_mode().value)")

if [ "$STATE" = "MAINTENANCE" ]; then
    echo "CRITICAL: Agent in MAINTENANCE mode"
    exit 2
fi

# Check Qdrant
curl -sf http://localhost:6333/healthz > /dev/null
if [ $? -ne 0 ]; then
    echo "CRITICAL: Qdrant is down"
    exit 2
fi

echo "OK: System healthy"
exit 0
```

### Backup Strategy

**Daily backup** (cron):
```bash
0 4 * * * /home/ktundepo/scripts/backup.sh
```

**`scripts/backup.sh`**:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/backups/ktundepo"

# Backup Qdrant
docker exec qdrant-container tar czf - /qdrant/storage > "$BACKUP_DIR/qdrant_$DATE.tar.gz"

# Backup state
cp agent/state.json "$BACKUP_DIR/state_$DATE.json"

# Backup reports (last 30 days)
find _reports -mtime -30 -type f | tar czf "$BACKUP_DIR/reports_$DATE.tar.gz" -T -

# Git push
cd /home/ktundepo/ktunDepo
git push origin main

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -mtime +30 -delete
```

---

## Roadmap

### Phase 1: Stabilization (Current)
- [x] Implement intake agent CLI
- [x] Add vision support for scanned materials
- [x] Create detailed reporting system
- [x] Implement HINT.json manual override system for folder ingestion
- [ ] Fix quality_checker.py page count bug
- [ ] Add comprehensive tests

### Phase 2: Telegram Bot Improvements
- [ ] Fix `successful_payment` async syntax error
- [ ] Implement `pre_checkout_query` handler
- [ ] Add resilient error handling for payment fulfillment
- [ ] Optimize database queries with concurrent execution
- [ ] Enforce `await` on all Telegraf context methods

### Phase 3: Enhancement
- [ ] Web interface for `_review/` queue
- [ ] Student search API
- [ ] Advanced analytics dashboard
- [ ] Multi-language support (English materials)
- [ ] Mobile app integration

### Phase 4: Scale
- [ ] Multi-university support
- [ ] Federated repository network
- [ ] Blockchain-based contribution tracking
- [ ] AI-powered study recommendations

---

## Contributing

See [README.md](README.md) for contribution guidelines.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contact

- **Website**: [ktun.not.tr](https://ktun.not.tr)
- **GitHub**: [c4kar/ktunDepo](https://github.com/c4kar/ktunDepo)

---

**Last Updated**: 2026-03-11  
**Version**: 2.1.0 (Intake Agent HINT Update)
