![Omi Logo](assets/logo.svg)

# Omi — Multi-Agent Platform

A production-ready platform for building, orchestrating, and deploying autonomous coding agents at scale. Omi provides a unified framework where specialist agents collaborate to tackle complex software engineering tasks.

## What is Omi?

Omi is a **multi-agent orchestration platform** designed for autonomous code generation, review, planning, and research. Instead of a monolithic AI, Omi routes tasks to specialized agents that work together:

- **Helix** (Coding Agent) — writes, tests, commits, and ships code
- **Explorer** — reads code, searches symbols, understands architecture  
- **Planner** — decomposes features into structured GitHub issues
- **Researcher** — searches the web for docs, APIs, and best practices
- **Triager** — categorizes and manages issue backlogs

The platform intelligently routes each user request to the right agent (or agents) and streams results in real-time.

---

## Core Features

### 🧠 Multi-Agent Orchestration
- **LangGraph StateGraph** — explicit, auditable decision flow
- **Keyword + LLM routing** — fast heuristics backed by Claude for ambiguous tasks
- **Specialist agents** — each agent optimized for a single responsibility
- **Collaborative chains** — agents can call each other sequentially

### 🔐 Security & Isolation
- **Git worktree isolation** — each code modification on a safe branch (`omi/*`)
- **Docker sandbox** — shell execution runs in memory-limited containers
- **Read-only access controls** — Explorer and Researcher have no write permissions
- **No API key exposure** — all LLM credentials stay server-side

### 📊 Observability
- **Token & cost tracking** — per-agent usage metrics
- **Task history** — full audit log of all operations
- **Real-time streaming** — WebSocket support for live progress updates
- **Health monitoring** — automatic agent heartbeat + offline detection

### ⚡ Production Ready
- **REST + WebSocket API** — sync and async task submission
- **FastAPI** — async-first, high-performance
- **SQLAlchemy ORM** — PostgreSQL or SQLite, migration-friendly
- **Multi-LLM support** — Anthropic Claude, OpenAI GPT, Ollama (local)

---

## Platform Architecture

![Omi Architecture Diagram](assets/architecture.png)

**Architecture Overview:**

- **Client Layer** — React dashboard streams tasks via HTTP + WebSocket
- **Platform Layer** — FastAPI gateway with pluggable components:
  - **Task Router** — routes by keyword heuristics or LLM judgment
  - **Agent Registry** — tracks availability, capabilities, health
  - **Storage** — persistent task history, sessions (SQLite or PostgreSQL)
  - **Observability** — token counting, cost tracking, latency metrics
- **Agent Layer** — five specialist agents, each with isolated toolsets:
  - **Helix** — code generation, testing, commits (write access)
  - **Explorer** — code search, architecture review (read-only)
  - **Planner** — feature decomposition into issues
  - **Researcher** — web search, documentation lookup
  - **Triager** — issue labeling, backlog management

Each agent runs in a **git worktree** (safe branching) with **Docker sandbox** for shell execution. Read-only agents cannot write code or create PRs.

---

## Installation

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** (for dashboard)
- **Ollama** (for local inference, or use Anthropic/OpenAI API keys)
- **Git** (for code operations)

### Quick Start

#### 1. Clone the Repository
```bash
git clone https://github.com/addy1997/omi.git
cd omi
```

#### 2. Install the Platform
```bash
pip install -e platform/
```

#### 3. Install Helix Agent
```bash
pip install -e agents/helix/
```

#### 4. Configure Environment Variables

**For the platform** (`platform/.env`):
```bash
cp platform/.env.example platform/.env
# Edit platform/.env with:
PLATFORM_SECRET_KEY=your-secret-key
PLATFORM_DB_URL=sqlite+aiosqlite:///./platform.db
ANTHROPIC_API_KEY=sk-ant-...  # or leave empty for Ollama
PLATFORM_ROUTER_MODEL=anthropic/claude-haiku-4-5
```

**For Helix** (`agents/helix/.env`):
```bash
cp agents/helix/.env.example agents/helix/.env
# Edit with:
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
GITHUB_OWNER=your-username
OMI_SUPERVISOR_MODEL=ollama/llama3.2
OMI_CODER_MODEL=ollama/qwen2.5-coder:7b
```

#### 5. Start Ollama (if using local models)
```bash
ollama serve
```

In a new terminal, pull the models:
```bash
ollama pull llama3.2
ollama pull qwen2.5-coder:7b
```

#### 6. Start the Services

**Terminal 1 — Platform API:**
```bash
omi-platform serve --port 9000
```

**Terminal 2 — Helix Agent:**
```bash
cd agents/helix
helix serve-agent --platform http://localhost:9000
```

**Terminal 3 — Dashboard:**
```bash
cd dashboard
npm install
npm run dev
```

#### 7. Access the Dashboard
Open **http://localhost:5173** in your browser.

---

## Usage

### Via Web Dashboard
1. Go to **http://localhost:5173**
2. Select **Chat** tab
3. Submit a task: `"Add a feature to parse JSON files"`
4. Watch the platform auto-route to **Helix** (Coder)
5. View results in the chat, task history, and metrics

### Via CLI
```bash
# Interactive chat with Helix
helix chat

# Start as standalone server (no platform)
helix serve

# Print session history
helix history <session-id>
```

### Via REST API
```bash
# Submit a task
curl -X POST http://localhost:9000/tasks \
  -H "Content-Type: application/json" \
  -d '{"message": "Review my code", "session_id": "abc123"}'

# Check agent status
curl http://localhost:9000/health

# List registered agents
curl http://localhost:9000/agents

# Get usage metrics
curl http://localhost:9000/tasks/usage/summary
```

### Via WebSocket
```javascript
const ws = new WebSocket('ws://localhost:9000/ws/session-123');
ws.send(JSON.stringify({ message: 'Generate a test file' }));
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

---

## Agent Capabilities

### Helix (Coder)
**Task Types:** Feature implementation, bug fixes, refactoring, testing

**Tools:**
- File read/write/edit (surgical, line-aware)
- Git (clone, worktree, commit, push)
- GitHub (PRs, issues, code search)
- Shell (run tests, build scripts)
- Tree-sitter AST (semantic code search)

**Example:**
```
User: "Add error handling to the payment module"
→ Helix explores the codebase
→ Creates a worktree (omi/payment-errors)
→ Edits payment.py with try/except blocks
→ Runs tests
→ Creates a PR on GitHub
```

### Explorer
**Task Types:** Code review, architecture questions, symbol search

**Tools:** Read-only file access, grep, AST symbol lookup, Git blame/log

**Example:**
```
User: "How is authentication implemented?"
→ Explorer searches for auth-related code
→ Returns architecture overview and file references
```

### Planner
**Task Types:** Feature decomposition, roadmap planning

**Tools:** Issue creation, labeling, GitHub integration

**Example:**
```
User: "Break down a user dashboard into tasks"
→ Planner generates 5 GitHub issues
→ Assigns labels (frontend, backend, testing)
→ Orders by dependency
```

### Researcher
**Task Types:** Documentation lookup, error investigation, API learning

**Tools:** DuckDuckGo web search, Jina URL reader

**Example:**
```
User: "How do I implement OAuth2 in FastAPI?"
→ Researcher finds top results
→ Extracts code examples and docs
```

### Triager
**Task Types:** Issue categorization, backlog management

**Labels:** MAJOR_BUG, BUG, LOW_HANGING_FRUIT, ENHANCEMENT, QUESTION, DUPLICATE, STALE

**Example:**
```
User: "Triage our open issues"
→ Triager reads and labels each issue
→ Closes duplicates
```

---

## Configuration

### Model Selection
Edit `.env` files to swap LLM providers:

**Anthropic Claude:**
```
OMI_CODER_MODEL=anthropic/claude-sonnet-4-5
OMI_SUPERVISOR_MODEL=anthropic/claude-haiku-4-5
```

**OpenAI:**
```
OMI_CODER_MODEL=openai/gpt-4o
OMI_SUPERVISOR_MODEL=openai/gpt-4o-mini
```

**Ollama (local):**
```
OMI_CODER_MODEL=ollama/qwen2.5-coder:7b
OMI_SUPERVISOR_MODEL=ollama/llama3.2
```

### Storage Backend
Default: SQLite (zero setup)

For production, use PostgreSQL:
```bash
# platform/.env
PLATFORM_DB_URL=postgresql+psycopg://user:pass@localhost:5432/omi

# agents/helix/.env
OMI_DB_URL=postgresql+psycopg://user:pass@localhost:5432/helix
```

### Docker Sandbox
By default, shell commands run in Docker containers for safety.

To use unsafe subprocess (dev only):
```
OMI_SANDBOX=subprocess
```

---

## Project Structure

```
omi/
├── agents/helix/              Helix coding agent
│   ├── helix/
│   │   ├── agents/            Specialist sub-agents (coder, explorer, etc.)
│   │   ├── supervisor/        LangGraph orchestration
│   │   ├── tools/             Code, git, GitHub, search, shell, AST
│   │   ├── memory/            Session & knowledge persistence
│   │   ├── cli.py             Command-line interface
│   │   └── platform_adapter.py Platform integration
│   └── pyproject.toml
│
├── platform/                  Omi platform core
│   ├── omi_platform/
│   │   ├── api/               REST API & WebSocket
│   │   ├── registry/          Agent discovery & health
│   │   ├── dispatcher/        Task routing & execution
│   │   ├── storage/           Task persistence
│   │   ├── observability/     Token/cost tracking
│   │   ├── auth/              JWT authentication
│   │   └── sdk/               Agent base classes
│   └── pyproject.toml
│
├── dashboard/                 React web UI
│   ├── src/
│   │   ├── pages/             Chat, Agents, Tasks, Metrics
│   │   ├── api.ts             Platform API client
│   │   └── App.tsx
│   └── package.json
│
├── docker-compose.yml         Full stack (platform + helix + dashboard + postgres)
├── LICENSE                    Apache 2.0
└── README.md
```

---

## Development

### Running Tests
```bash
# Helix tests
cd agents/helix
pytest -v

# Platform tests
cd platform
pytest -v
```

### Type Checking
```bash
# All projects
mypy agents/helix/helix
mypy platform/omi_platform
```

### Code Style
```bash
ruff check .
ruff format .
```

---

## Roadmap

- [ ] **Vision agents** — image analysis for design review
- [ ] **Deployment agents** — auto-deploy to AWS/GCP/Azure
- [ ] **Data agents** — SQL generation, data analysis
- [ ] **Team collaboration** — shared workspaces, agent auditing
- [ ] **Custom agent SDK** — user-defined agents with tool composition
- [ ] **Marketplace** — agent publishing and discovery

---

## Contributing

We welcome contributions! Please:

1. Fork the repo
2. Create a branch (`git checkout -b feature/your-feature`)
3. Commit with clear messages
4. Push and open a PR

See [LICENSE](LICENSE) for terms (Apache 2.0).

---

## License

This project is licensed under the **Apache License 2.0** — see [LICENSE](LICENSE) for details.

---

## Support

- **Docs:** [github.com/addy1997/omi](https://github.com/addy1997/omi)
- **Issues:** [GitHub Issues](https://github.com/addy1997/omi/issues)
- **Email:** adwaitnaik27@gmail.com

---

**Built with** LangGraph • FastAPI • React • Ollama • Claude

