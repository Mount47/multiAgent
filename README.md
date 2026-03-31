# Multi-Agent Software Development Collaboration System

基于 Microsoft AutoGen 0.4 构建的多 Agent 协作开发框架。5 个专业角色（ProductManager、Architect、Coder、Tester、Reviewer）通过有限状态机驱动，完成需求分析 → 系统设计 → 代码生成 → 单元测试 → 代码评审的全自动化开发流程。

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Entry Points                          │
│    CLI (agent-dev)          API Server (agent-dev-api)      │
│                             FastAPI + WebSocket :8000       │
│                                                             │
│    Web UI (Vite + React + TypeScript)   :5173               │
├─────────────────────────────────────────────────────────────┤
│                    Orchestration Layer                       │
│   SelectorGroupChat  ←→  WorkflowStateMachine (7 states)   │
├──────────┬──────────┬───────────┬───────────┬───────────────┤
│  Agents  │  Tools   │  Memory   │  Models   │ Observability │
│  5 roles │  7 funcs │  ChromaDB │  4 provs  │ Tracer+Metric │
└──────────┴──────────┴───────────┴───────────┴───────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (frontend)
- At least one LLM API key (Gemini / OpenAI / DeepSeek / Ollama)

### 1. Backend Setup

```bash
# Clone & create virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -e ".[api,memory,dev]"

# Configure environment
cp .env.example .env
# Edit .env — set your API key and default model
```

### 2. Frontend Setup

```bash
cd web
npm install
```

### 3. Run

```bash
# Terminal 1 — API server
agent-dev-api

# Terminal 2 — Web UI
cd web
npm run dev
```

Open http://localhost:5173

### CLI Mode (no UI)

```bash
agent-dev "Build a Python calculator with add, subtract, multiply, divide"
```

## Project Structure

```
├── config/
│   ├── models.yaml            # LLM provider config (Gemini/OpenAI/DeepSeek/Ollama)
│   ├── workflows.yaml         # State machine definition (states, transitions, guards)
│   ├── settings.py            # Pydantic settings from .env
│   └── prompts/               # Agent system prompts (Markdown)
│       ├── product_manager.md
│       ├── architect.md
│       ├── coder.md
│       ├── tester.md
│       └── reviewer.md
├── src/
│   ├── cli.py                 # CLI entry point
│   ├── agents/                # 5 Agent roles + factory
│   ├── orchestration/         # FSM + SelectorGroupChat bridge
│   ├── tools/                 # 7 tool functions + role registry
│   │   └── instrumented.py    # Async wrappers + tool observability decorator
│   ├── memory/                # ChromaDB vector store (conversations + code)
│   ├── models/                # LLM client factory (4 providers)
│   ├── persistence/           # SQLite + SQLAlchemy async
│   ├── observability/         # WorkflowTracer + MetricsCollector
│   │   └── tool_observer.py   # Tool call chain observer
│   └── api/                   # FastAPI REST + WebSocket
├── web/                       # React frontend (Vite + TypeScript + Tailwind)
│   └── src/
│       ├── components/        # UI components (21 files)
│       ├── hooks/             # Custom hooks (5 files)
│       ├── api/               # REST client + WebSocket hook
│       └── types/             # TypeScript type definitions
├── tests/
│   ├── unit/                  # 10 test files
│   └── integration/
└── docs/
    └── IMPLEMENTATION_GUIDE.md  # Detailed implementation status & roadmap
```

## Workflow

```
requirements_analysis (PM)
        ↓
architecture_design (Architect)
        ↓
     coding (Coder)
        ↓
    testing (Tester)
        ↓
  code_review (Reviewer)
      ↓           ↓
  approved    revision (Coder) → testing → code_review → ...
```

- **Guards** determine transitions: `tests_passed`, `tests_failed`, `review_approved`, `review_revision_needed`
- Max 30 rounds, max 3 revision iterations
- Configurable via `config/workflows.yaml`

## Agent Roles

| Role | Responsibility | Tools |
|------|---------------|-------|
| **ProductManager** | Requirement analysis, structured feature specs | — |
| **Architect** | System design, module/interface definition | search_memory |
| **Coder** | Code generation, file I/O, dependency management | execute_code, write_file, read_file, install_dependency, search_memory, save_to_memory |
| **Tester** | Test writing & execution | execute_code, run_tests, read_file |
| **Reviewer** | Code review, APPROVED/REVISE verdict | — |

## Tool System

| Tool | Description | Security |
|------|-------------|----------|
| `execute_code` | Run Python in subprocess | 30s timeout |
| `write_file` | Write to workspace | Path traversal protection |
| `read_file` | Read from workspace | Workspace-scoped |
| `run_tests` | Execute pytest | 60s timeout |
| `install_dependency` | pip install | Command injection protection |
| `search_memory` | ChromaDB cosine search | Read-only |
| `save_to_memory` | Store to ChromaDB | Append-only |

Tools are registered per-role via `src/tools/registry.py`.

## Model Providers

Configured in `config/models.yaml`. All use OpenAI-compatible API:

| Provider | Model | Env Var |
|----------|-------|---------|
| Gemini | gemini-2.0-flash | `GEMINI_API_KEY` |
| OpenAI | gpt-4o | `OPENAI_API_KEY` |
| DeepSeek | deepseek-chat | `DEEPSEEK_API_KEY` |
| Ollama (local) | qwen2.5:7b | — (localhost:11434) |

Set `DEFAULT_MODEL` in `.env` to choose the default provider.

## Web UI Features

| Feature | Description |
|---------|-------------|
| Task Creation | Input task description + select model provider |
| Workflow Graph | SVG state diagram with real-time node highlighting |
| Event Stream | Live agent output via WebSocket, color-coded by role |
| Task History | Browse and revisit past tasks |
| Code Display | Syntax-highlighted view of generated files |
| Metrics Dashboard | Workflow stats, agent call frequency, duration charts |
| Trace Timeline | Visual execution timeline with per-state duration |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tasks` | Create a new workflow task |
| GET | `/api/tasks` | List all tasks |
| GET | `/api/tasks/{id}` | Get task detail with events |
| WS | `/api/tasks/ws/{id}` | Real-time event stream |
| GET | `/api/providers` | List available LLM providers |
| GET | `/api/workflow/graph` | Get state machine topology |
| GET | `/api/workspace/files` | List generated code files |
| GET | `/api/metrics` | Aggregated workflow metrics |
| GET | `/api/traces/{id}` | Execution trace for a task |
| GET | `/healthz` | Health check |

## Observability

- **WorkflowTracer** — per-task trace with state transitions, duration, prompt/completion token split
- **Tool call chain** — each tool invocation records sanitized input, output, duration, success/failure, traceback
- **MetricsCollector** — aggregated workflow stats, transition counts, token totals, agent call frequency
- **Error tracking** — workflow exceptions are persisted as `TaskEvent(source=system_error)` with full traceback
- Data exposed via `/api/metrics` and `/api/traces/{task_id}` (`tool_calls` included in trace payload)

## Configuration

Key environment variables (see `.env.example`):

```env
DEFAULT_MODEL=gemini              # Provider name from models.yaml
GEMINI_API_KEY=your-key-here
WORKSPACE_DIR=./workspace         # Agent file output directory
LOG_LEVEL=INFO
MAX_WORKFLOW_ROUNDS=30
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
```

## Testing

```bash
pytest                    # Run all unit tests
pytest tests/unit -v      # Verbose unit tests
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Framework | AutoGen 0.4 (SelectorGroupChat) |
| Backend | FastAPI + WebSocket + SQLAlchemy Async |
| Frontend | Vite + React 18 + TypeScript + Tailwind CSS v4 |
| Charts | Recharts |
| Vector DB | ChromaDB |
| Database | SQLite (aiosqlite) |
| LLM Interface | OpenAI-compatible API |
| Testing | pytest + pytest-asyncio |

## License

MIT
