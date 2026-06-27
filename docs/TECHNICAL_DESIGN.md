# Omi Platform — Technical Design Document

**Version:** 0.1.0  
**Last Updated:** June 2026  
**Status:** Active Development

---

## 1. Executive Summary

Omi Platform is a **multi-agent orchestration system** that enables seamless integration and management of distributed AI agents. It provides:

- **Single entry point** for all clients to submit tasks to a pool of agents
- **Intelligent routing** that matches tasks to the best available agent based on capability, keywords, or LLM decision
- **Task chaining** where outputs of one task feed into the next for multi-step workflows
- **Collaboration mode** to solicit simultaneous responses from multiple agents
- **Built-in observability** for cost tracking, token usage, and performance metrics
- **Zero external API dependency** — agents run independently, platform only coordinates

---

## 2. Architectural Principles

### 2.1 Core Principles

| Principle | Description |
|-----------|-------------|
| **Agent Autonomy** | Agents are self-contained services with their own lifecycle. The platform does not manage agent internals. |
| **Stateless Routing** | Task routing is deterministic: explicit → capability hint → keyword match → LLM fallback. |
| **Heartbeat-driven Status** | Agents must heartbeat every 30s or they're marked offline. No polling from platform. |
| **Request-scoped Context** | Task context and metadata flow through the chain; no persistent session state on platform. |
| **Cost & Token Transparency** | Every task result tracks tokens, cost, and duration for billing and optimization. |
| **Security by Default** | JWT authentication, CORS restrictions, trusted host validation, security headers on all responses. |

### 2.2 Design Trade-offs

| Choice | Why | Trade-off |
|--------|-----|-----------|
| **Heartbeat (pull) over WebSocket (push)** | Simple, stateless monitoring for distributed agents | Agents must implement heartbeat loop; slower failure detection |
| **Keyword + LLM routing over ML ranking** | Fast fallback without dependencies on training infrastructure | Less optimal for novel task types; LLM routing adds ~15ms latency |
| **In-process SQLite vs. separate DB** | Easier deployment in dev/single-server scenarios | Not suitable for large-scale multi-instance deployments |
| **Task chain vs. explicit graph** | Simple, easy to reason about sequential dependencies | No support for parallel task execution or complex DAGs |

---

## 3. System Components

### 3.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Omi Platform (9000)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐   │
│  │   API Gateway    │  │   WebSocket      │  │   Auth (JWT) │   │
│  │   (FastAPI)      │  │   Streaming      │  │              │   │
│  └────────┬─────────┘  └────────┬─────────┘  └──────────────┘   │
│           │                     │                                 │
│  ┌────────▼─────────────────────▼──────────────────────────────┐ │
│  │              Route Manager (Task → Agent)                   │ │
│  │  ▪ Explicit routing (agent_id specified)                    │ │
│  │  ▪ Capability matching (metadata hint)                      │ │
│  │  ▪ Keyword detection (message analysis)                     │ │
│  │  ▪ LLM routing fallback (claudehaiku)                       │ │
│  └────────┬──────────────────────────────────────────────────┘  │
│           │                                                       │
│  ┌────────▼──────────────┐  ┌────────────────────────────────┐  │
│  │  Registry (Store)     │  │  Task Executor                 │  │
│  │  ▪ Agent registration │  │  ▪ HTTP call to agent /run     │  │
│  │  ▪ Heartbeat tracking │  │  ▪ Timeout handling            │  │
│  │  ▪ Status monitoring  │  │  ▪ Result persistence          │  │
│  └───────────────────────┘  └───────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Storage Layer (SQLAlchemy + Async)              │   │
│  │  ▪ TaskRecord (task execution history)                  │   │
│  │  ▪ AgentRecord (agent registry)                         │   │
│  │  ▪ UsageRecord (cost & token tracking)                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│           │           │           │                              │
│  ┌────────▼──┐ ┌──────▼──┐ ┌─────▼────┐  ┌──────────────────┐  │
│  │ Observ.   │ │ Auth    │ │ Config   │  │ Collaboration    │  │
│  │ Tracker   │ │ (JWT)   │ │ Manager  │  │ Tools            │  │
│  └───────────┘ └─────────┘ └──────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         ▲         ▲       ▲         ▲
         │         │       │         │
         │ HTTP    │ HTTP  │ HTTP    │ HTTP
    ┌────┴─┐  ┌────┴─┐  ┌─┴───┐   ┌┴───────┐
    │Agent1│  │Agent2│  │Agent3│   │Agent N │
    │ :8001│  │ :8002│  │ :8003│   │ :XXXX  │
    └──────┘  └──────┘  └──────┘   └────────┘
```

### 3.2 Component Descriptions

#### **API Gateway (FastAPI)**
- Single HTTP entry point for all clients
- Defines routes: `/agents`, `/tasks`, `/auth`, `/health`, `/ws`
- Middleware: CORS, trusted host validation, security headers
- Lifespan management: initializes registry, storage, observability on startup

**Responsibilities:**
- Accept task submissions (REST + WebSocket)
- Route HTTP requests to appropriate handlers
- Enforce authentication via JWT tokens
- Stream WebSocket results in real-time

---

#### **Route Manager (Dispatcher)**
Intelligent task-to-agent mapping using a 4-level cascade:

1. **Explicit** — `task.agent_id` is set → direct route (no LLM)
2. **Capability Hint** — `task.metadata["capability"]` matches a tag → find agents with that capability
3. **Keyword Matching** — Analyze message for patterns (e.g., "write", "test", "deploy") → infer capabilities
4. **LLM Fallback** — Ask Claude Haiku to pick the best agent from available pool

**Trade-off:** Levels 1-3 are fast (< 10ms); level 4 adds ~15ms but is semantically aware.

---

#### **Registry Store**
Maintains source of truth for agent availability and capabilities.

**Core Operations:**
- `register_agent()` — Agent joins (idempotent; re-register = update)
- `deregister_agent()` — Agent leaves (removes from registry)
- `heartbeat()` — Agent pings every 30s; updates `last_heartbeat` and sets status to ONLINE
- `list_agents()` — Query by status (ONLINE/OFFLINE/BUSY) or capability
- `find_agents_for_task()` — Return online agents matching ANY of given capabilities

**Background Process:**
- Health monitor runs every 30s
- Marks agents OFFLINE if `now() - last_heartbeat > 90s`
- Prevents zombie agents from receiving tasks

---

#### **Task Executor**
Orchestrates task submission and result persistence.

**Flow:**
1. Save incoming task to storage (status=PENDING)
2. Route task to an agent via Route Manager
3. Call agent's `/run` endpoint (300s timeout)
4. Persist TaskResult to storage
5. Record usage (tokens, cost, duration) in tracker

**Modes:**
- **Single:** `submit(task)` — one task, one agent
- **Chain:** `submit_chain([task1, task2, ...])` — output of N becomes context for N+1; stops on first failure
- **Collaborate:** `collaborate(message, [agent_ids])` — send same message to multiple agents; join results

---

#### **Storage Layer (SQLAlchemy + SQLite)**
Three tables: TaskRecord, AgentRecord, UsageRecord

**TaskRecord** — Immutable log of every task execution
- Indexed by: session_id, agent_id
- Fields: status, result (content), tokens_used, cost_usd, duration_ms, error

**AgentRecord** — Agent registry
- Indexed by: name, status, capabilities_csv
- Fields: base_url, version, registered_at, last_heartbeat, metadata_json

**UsageRecord** — Cost & performance tracking
- Indexed by: task_id, agent_id
- Fields: tokens_used, cost_usd, duration_ms, status, recorded_at

---

#### **Authentication (JWT)**
- Tokens issued at `/auth/token` after validating username/password
- Token embedded in WebSocket query param: `ws://host:9000/ws/SESSION_ID?token=JWT_TOKEN`
- Tokens expire after 24 hours (configurable)
- In production: integrate with real auth backend (LDAP, OAuth2, etc.)

---

#### **Observability Tracker**
Real-time tracking of platform usage across all agents.

**Metrics:**
- Total tasks executed
- Total tokens consumed (for billing)
- Total cost (USD)
- Average duration per task
- Per-agent breakdowns

**APIs:**
- `get_usage_summary(agent_id=None)` — Platform-wide or per-agent stats
- `get_per_agent_usage()` — Breakdown across all agents

---

#### **Agent SDK (agent_base.py)**
Base class + utilities every agent must implement.

**AgentBase Class:**
- Abstract method: `async handle(task: Task) → TaskResult`
- Lifecycle: `register()`, `deregister()`, `send_heartbeat()`
- Health check: `health_check()` — custom health logic

**Helper: `make_agent_server(agent)`**
Returns a FastAPI app with three standard endpoints:
- `POST /run` → `agent.handle(task)` (wraps duration & error handling)
- `GET /health` → `agent.health_check()` → `{"status": "ok"|"degraded"}`
- `GET /info` → `agent.agent_info()` → AgentInfo metadata

---

### 3.3 Data Models

#### **Task**
```
id: str (UUID)
message: str (user prompt, ≤10KB)
session_id: str (UUID; groups related tasks)
agent_id: str | None (explicit routing; auto-route if None)
context: dict (arbitrary client data, passed through chain)
parent_task_id: str | None (for multi-step tracking)
metadata: dict (user identity, role, capability hint)
created_at: datetime (UTC)
```

#### **TaskResult**
```
task_id: str (echoes Task.id)
agent_id: str (resolved agent)
status: TaskStatus (COMPLETED | FAILED | PENDING | RUNNING | CANCELLED)
content: str (agent response)
tokens_used: int (for billing)
cost_usd: float (calculated by agent)
duration_ms: int (end-to-end execution time)
error: str | None (error message if status=FAILED)
artifacts: dict (files, PRs, issues created by agent)
completed_at: datetime (UTC)
```

#### **AgentInfo**
```
id: str (unique agent identifier)
name: str (human-readable name)
description: str (what agent does)
capabilities: list[str] (tags: code_generation, testing, etc.)
version: str (semver)
base_url: str (http://host:port where agent runs)
api_key: str (optional; for secured agent endpoints)
status: AgentStatus (ONLINE | OFFLINE | BUSY | ERROR)
registered_at: datetime
last_heartbeat: datetime
metadata: dict (arbitrary agent metadata)
```

#### **Capability Tags**
```
CODE_GENERATION   — write, implement, create code
CODE_REVIEW       — review PRs, diffs, audits
CODE_SEARCH       — find code, locate files
PLANNING          — break down tasks, create roadmaps
ISSUE_TRIAGE      — categorize, label issues
WEB_RESEARCH      — lookup docs, external research
DATA_ANALYSIS     — analyze data, charts, stats
DEVOPS            — deploy, CI/CD, infrastructure
DOCUMENTATION     — write docs, comments
TESTING           — write tests, coverage analysis
GENERAL           — fallback; can do anything
```

---

## 4. API Contracts

### 4.1 Task Submission

#### **REST: Single Task**
```
POST /tasks
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>

{
  "message": "Write a unit test for the login function",
  "session_id": "user-session-123",
  "agent_id": null,
  "context": {"file": "auth.py", "framework": "pytest"},
  "metadata": {"capability": "testing"}
}

Response (200):
{
  "task_id": "abc123",
  "agent_id": "testing-agent-01",
  "status": "completed",
  "content": "Here's a unit test...",
  "tokens_used": 340,
  "cost_usd": 0.000051,
  "duration_ms": 1240,
  "error": null,
  "artifacts": {},
  "completed_at": "2026-06-08T14:32:10Z"
}
```

#### **WebSocket: Streaming**
```
WebSocket: /ws/{session_id}?token=<JWT_TOKEN>

Client sends:
{
  "message": "Analyze this bug report",
  "agent_id": null,
  "context": {"bug_id": "ISSUE-42"}
}

Server streams:
{"type": "start"}
{"type": "result", "task_id": "...", "agent_id": "...", "content": "...", ...}
{"type": "done"}

Or on error:
{"type": "error", "content": "Task execution failed"}
```

#### **Task Chaining**
```
POST /tasks/chain
Content-Type: application/json

[
  {
    "message": "Identify security issues in this code snippet",
    "metadata": {"capability": "code_review"}
  },
  {
    "message": "Based on the issues found, write a fix",
    "metadata": {"capability": "code_generation"}
  }
]

Response:
[
  {
    "task_id": "task1",
    "agent_id": "code-review-agent",
    "status": "completed",
    "content": "Found: SQL injection in line 42..."
  },
  {
    "task_id": "task2",
    "agent_id": "code-gen-agent",
    "status": "completed",
    "content": "Here's the fixed code...",
    "context": {
      "prior_result": "Found: SQL injection in line 42..."
    }
  }
]
```

#### **Collaboration**
```
POST /tasks/collaborate
Content-Type: application/json

{
  "message": "Should we migrate to async/await?",
  "agent_ids": ["python-expert", "performance-expert"],
  "session_id": "sprint-planning-1"
}

Response:
{
  "result": "
    **[python-expert]**
    Async/await improves...
    
    ---
    
    **[performance-expert]**
    From a perf standpoint...
  "
}
```

### 4.2 Agent Management

#### **Register Agent**
```
POST /agents/register
Content-Type: application/json

{
  "id": "coding-agent-01",
  "name": "Coding Agent",
  "description": "Writes and reviews code",
  "capabilities": ["code_generation", "code_review"],
  "version": "1.2.3",
  "base_url": "http://localhost:8001",
  "api_key": "optional-agent-secret"
}

Response (200):
(echoes input with status=ONLINE, registered_at, last_heartbeat)
```

#### **Heartbeat (Keep-Alive)**
```
POST /agents/{agent_id}/heartbeat

Response (200):
{"status": "ok"}

Response (404):
{"detail": "Agent not found"}
```

#### **List Agents**
```
GET /agents?capability=code_generation&status=online

Response:
[
  {
    "id": "agent-01",
    "name": "...",
    "description": "...",
    "capabilities": ["code_generation"],
    "status": "online",
    "last_heartbeat": "2026-06-08T14:30:00Z",
    ...
  },
  ...
]
```

#### **Get Agent Details**
```
GET /agents/{agent_id}

Response:
{
  "id": "agent-01",
  "name": "Coding Agent",
  "description": "...",
  "capabilities": [...],
  "version": "1.2.3",
  "base_url": "http://localhost:8001",
  "status": "online",
  "registered_at": "2026-06-01T10:00:00Z",
  "last_heartbeat": "2026-06-08T14:32:00Z",
  "metadata": {}
}
```

#### **Deregister Agent**
```
DELETE /agents/{agent_id}
Authorization: Bearer <JWT_TOKEN>

Response (200):
{"status": "removed", "agent_id": "agent-01"}
```

### 4.3 Query & Analytics

#### **Task History**
```
GET /tasks?session_id=sess-123&agent_id=agent-01&limit=50

Response:
[
  {
    "id": "task-abc",
    "message": "Write a test",
    "status": "completed",
    "result": "...",
    "tokens_used": 340,
    "cost_usd": 0.000051,
    "duration_ms": 1240,
    "created_at": "...",
    "completed_at": "...",
    ...
  },
  ...
]
```

#### **Usage Summary**
```
GET /usage/summary?agent_id=agent-01

Response:
{
  "total_tasks": 150,
  "total_tokens": 45230,
  "total_cost_usd": 0.0081,
  "avg_duration_ms": 1540,
  "agent_id": "agent-01"
}
```

#### **Per-Agent Usage**
```
GET /usage/per-agent

Response:
[
  {"agent_id": "agent-01", "tasks": 150, "tokens": 45230, "cost_usd": 0.0081},
  {"agent_id": "agent-02", "tasks": 320, "tokens": 98100, "cost_usd": 0.0156},
  ...
]
```

### 4.4 Health & Status

#### **Platform Health**
```
GET /health

Response (200):
{
  "status": "ok",
  "platform": "Omi Platform",
  "version": "0.1.0",
  "online_agents": 3,
  "agents": [
    {"id": "agent-01", "name": "Coding Agent"},
    ...
  ]
}
```

#### **Readiness Probe (Kubernetes)**
```
GET /health/ready

Response (200):
{"ready": true}
```

---

## 5. Task Routing Flow

```
┌────────────────────────────────────────────────────────────────┐
│ Client submits Task (message, agent_id, context, metadata)     │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
        ┌─────────────────┐
        │ Agent ID set?   │
        └────┬────────┬───┘
             │NO      │YES
             │        └──────────────────────┐
             │                               │
             ▼                               ▼
        ┌──────────────────────┐       ┌────────────┐
        │ Capability in        │       │ Get agent  │
        │ metadata?            │       │ by ID from │
        └────┬────────┬────────┘       │ registry   │
             │NO      │YES            └─┬──────────┘
             │        │                  │
             │        └────┐         ┌───┴────────────┐
             │             │         │ Is ONLINE?     │
             │             │         └─┬──┬──────────┘
             │             │           │  │NO
             │             ▼           │  │
             │        ┌─────────────┐  │  └──→ Return FAILED
             │        │ Match       │  │
             │        │ agents with │  │ YES
             │        │ capability  │  │  │
             │        └─┬─────────┬─┘  │  ▼
             │          │SUCCESS  │    └─→ ROUTE TO AGENT
             │          │         │
             │          ▼    NO   ▼
             │       ROUTE   ┌──────────────┐
             │       TO     │ Keyword match │
             │       AGENT  │ in message?   │
             │              └────┬──────┬───┘
             │                   │ YES  │NO
             │                   │      │
             │                   ▼      ▼
             │              MATCH    ┌────────────────┐
             │              AGENTS   │ LLM route      │
             │              WITH     │ (Claude Haiku) │
             │              CAP      └────┬───────┬──┘
             │                            │SUCCESS│
             │                            ▼       ▼
             └────────────────────────→ ROUTE TO BEST AGENT
```

---

## 6. Task Execution Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│ Task Submitted to Platform                                      │
└────────────┬──────────────────────────────────────────────────┘
             │
             ▼
        ┌─────────────────┐
        │ 1. Save Task    │
        │    Status:      │ ─→ Database
        │    PENDING      │    (TaskRecord)
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ 2. Route Task   │
        │    (pick agent) │ ─→ Registry
        └────────┬────────┘
                 │
             ┌───┴────┐
             │ FOUND? │
             └───┬────┘
                 │
         ┌───────┴────────┐
         │NO              │YES
         │                │
         ▼                ▼
    FAILED         ┌──────────────┐
    (result)       │ 3. Call Agent│
    return         │    POST /run  │ ─→ HTTP timeout: 300s
                   └──────┬───────┘
                          │
                    ┌─────┴──────┐
                    │ SUCCESS?   │
                    └─────┬──┬───┘
                          │  │
                    ┌─────┘  └────┐
                    │             │
                    ▼             ▼
              ┌──────────┐    ┌──────────┐
              │ 4. Parse │    │ 4. Create│
              │ Result   │    │ Error    │
              │ status=  │    │ Result   │
              │ COMPLETED    │ status=  │
              └────┬─────┘    │ FAILED   │
                   │          └────┬────┘
                   │               │
                   └───────┬───────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ 5. Store Result │
                  │    to Database  │ ─→ TaskRecord
                  └────────┬────────┘     (updated)
                           │
                           ▼
                  ┌─────────────────┐
                  │ 6. Record Usage │ ─→ UsageRecord
                  │  (tokens, cost) │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ 7. Return       │
                  │ TaskResult      │ ─→ Client
                  │ to Client       │
                  └─────────────────┘
```

---

## 7. Architecture Diagrams

### 7.1 High-Level System Architecture

**Diagram Title:** "Omi Platform: Multi-Agent Orchestration"

```
[Generated via Excalidraw]

┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                         CLIENT LAYER                            │
│                                                                 │
│    Web UI (React)    |   Mobile App    |   CLI / Scripts        │
│                                                                 │
└────────────────┬──────────────────────────────────────┬────────┘
                 │ REST (Tasks, Agents, Queries)       │ WebSocket
                 │                                     │ Streaming
                 ▼                                     ▼
         ┌──────────────────────────────────────────────────┐
         │                                                  │
         │          OMI PLATFORM (Port 9000)               │
         │                                                  │
         │  ┌──────────────────────────────────────────┐  │
         │  │   API Gateway & Middleware Layer        │  │
         │  │   • CORS, Trusted Host, Security Headers│  │
         │  │   • JWT Authentication                  │  │
         │  │   • Request/Response Logging             │  │
         │  └────────────────────┬─────────────────────┘  │
         │                       │                         │
         │  ┌────────────────────▼─────────────────────┐  │
         │  │  Router (Task → Agent Mapping)          │  │
         │  │  1. Explicit (agent_id)                 │  │
         │  │  2. Capability hint (metadata)          │  │
         │  │  3. Keywords (message analysis)         │  │
         │  │  4. LLM (claude-haiku)                  │  │
         │  └────────────┬──────────────────────────┬─┘  │
         │               │                          │     │
         │  ┌────────────▼──────┐  ┌────────────────▼──┐ │
         │  │  Agent Registry   │  │  Task Executor    │ │
         │  │  • Register       │  │  • Async HTTP     │ │
         │  │  • Deregister     │  │  • Timeout Handle │ │
         │  │  • Heartbeat      │  │  • Chain Support  │ │
         │  │  • Status Track   │  │  • Collaborate    │ │
         │  └───────┬──────────┘  └────────┬──────────┘ │
         │          │                      │             │
         │  ┌───────┴──────────────────────▼───────────┐ │
         │  │    Storage Layer (SQLAlchemy)            │ │
         │  │                                          │ │
         │  │  • TaskRecord (execution history)        │ │
         │  │  • AgentRecord (agent registry)          │ │
         │  │  • UsageRecord (cost & tokens)           │ │
         │  └────────────────┬─────────────────────────┘ │
         │                   │                            │
         │  ┌────────────────▼──────────────────────────┐ │
         │  │  Observable Backing Services              │ │
         │  │                                          │ │
         │  │  Tracker:  Cost, tokens, duration        │ │
         │  │  Auth:     JWT issue, validate           │ │
         │  │  Config:   Settings management           │ │
         │  │  Collab:   Multi-agent synthesis         │ │
         │  └──────────────────────────────────────────┘ │
         │                                                  │
         └──────────────────────────────────────────────────┘
                 ▲              ▲           ▲
                 │              │           │
    HTTP POST /run  HTTP GET /info  HTTP GET /health
                 │              │           │
         ┌───────┴──────┬───────┴──┬───────┴──────┐
         │              │          │              │
         ▼              ▼          ▼              ▼
    [Agent 1]   [Agent 2]   [Agent 3]   [Agent N]
    Code Gen    Code Review  Data Analyzer  ...
    (Port 8001) (Port 8002)  (Port 8003)

    Each Agent:
    • Extends AgentBase
    • Implements handle(task) → TaskResult
    • Calls /register on startup
    • Heartbeats every 30s
    • Runs independent lifecycle
```

### 7.2 Task Routing Decision Tree

```
[Generated via Excalidraw]

┌──────────────────────┐
│ Task Arrives         │
│ message: string      │
│ agent_id: str | None │
│ context: dict        │
│ metadata: dict       │
└─────────┬────────────┘
          │
          ▼
    ┌─────────────┐
    │ Agent ID    │
    │ specified?  │
    └──┬──────┬───┘
       │YES   │NO
       │      │
       ▼      ▼
   ROUTE  ┌────────────────┐
   (fast) │ Capability in  │
          │ metadata       │
          │ ["capability"] │
          └──┬──────────┬──┘
             │YES       │NO
             │          │
             ▼          ▼
         ROUTE     ┌─────────────────────┐
         (match    │ Keyword scan        │
         by cap)   │ message.lower()     │
                   │ against patterns:   │
                   │ • "write"→code_gen  │
                   │ • "review"→review   │
                   │ • "test"→testing    │
                   │ • etc.              │
                   └──┬──────────┬───────┘
                      │MATCHED   │NO
                      │          │
                      ▼          ▼
                  ROUTE      ┌──────────────────┐
                  (fast)     │ LLM Route        │
                             │ (Claude Haiku)   │
                             │ "Pick the best   │
                             │ agent for: ..."  │
                             │                  │
                             │ Returns: agent_id│
                             └────┬─────────────┘
                                  │
                                  ▼
                            ┌──────────────┐
                            │ Query        │
                            │ Registry:    │
                            │ Get agent    │
                            │ by ID        │
                            │ Check status │
                            │ = ONLINE?    │
                            └──┬───────┬───┘
                               │YES    │NO
                               │       │
                               ▼       ▼
                           DISPATCH  FAILED
                           TO AGENT  (error)
                           (HTTP)
```

### 7.3 Agent Lifecycle State Machine

```
[Generated via Excalidraw]

                ┌─────────────────────────┐
                │ Agent Not Running       │
                │ (Unregistered)          │
                └───────────┬─────────────┘
                            │
                            │ Agent calls:
                            │ agent.register()
                            ▼
                ┌─────────────────────────┐
                │ ONLINE                  │
                │ ✓ Registered            │
                │ ✓ Heartbeat fresh       │
                │ ✓ Ready for tasks       │
                └──┬──────────────┬───────┘
                   │              │
                   │ Task         │ No heartbeat
                   │ arrives      │ for 90+ sec
                   ▼              │
        [Agent processes]         ▼
        [task.handle()]     ┌─────────────────────────┐
        [returns result]    │ OFFLINE                 │
                   │        │ ✗ Heartbeat stale       │
                   │        │ ✗ Dropped tasks         │
                   │        │ ✗ No routing to agent   │
                   │        └──┬────────────────┬──────┘
                   │           │                │
                   │           │ Agent restarts,│ Manual admin
                   │           │ heartbeats     │ deregister
                   │           ▼                ▼
                   │    ┌──────────────┐  ┌──────────────┐
                   │    │ ONLINE again │  │ Deregistered │
                   │    └──────────────┘  └──────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Task Complete        │
        │ (status in result)   │
        └──────────────────────┘
```

### 7.4 Task Chain Execution Flow

```
[Generated via Excalidraw]

Client submits:
[Task1, Task2, Task3]
to /tasks/chain

                ▼
        ┌──────────────────────┐
        │ Task 1 Submit        │
        │ message: "..."       │
        │ context: {}          │
        └──────┬───────────────┘
               │
               ▼
        ┌──────────────────────┐
        │ Route → Agent A      │
        │ Execute → Result 1   │
        │ status: COMPLETED    │
        │ content: "Output 1"  │
        └──────┬───────────────┘
               │
        ┌──────▼──────────────────────────────────┐
        │ SUCCESS: Extract content               │
        │ Store as prior_context                 │
        │ Check Task2                            │
        └──────┬───────────────────────────────┬─┘
               │                               │
               │ Task2 exists                  │ No Task2: DONE
               │                               │
               ▼                               ▼
        ┌──────────────────────────┐    [Return results]
        │ Task 2 Submit            │
        │ context: {               │
        │   prior_result: "Out 1"  │
        │ }                        │
        │ message: "..."           │
        └──────┬────────────────────┘
               │
               ▼
        ┌──────────────────────────┐
        │ Route → Agent B          │
        │ (uses prior_result)      │
        │ Execute → Result 2       │
        │ status: COMPLETED        │
        │ content: "Output 2"      │
        └──────┬────────────────────┘
               │
        ┌──────▼──────────────────────────────────┐
        │ SUCCESS: Extract content               │
        │ Store as prior_context                 │
        │ Check Task3                            │
        └──────┬───────────────────────────────┬─┘
               │                               │
               │ Task3 exists                  │ No Task3: DONE
               │                               │
               ▼                               ▼
        ┌──────────────────────────┐    [Return results]
        │ Task 3 Submit            │
        │ context: {               │
        │   prior_result: "Out 2"  │
        │ }                        │
        │ ...                      │
        └──────┬────────────────────┘
               │
               ▼
        [As above, chain continues]

        OR if Result N fails:
        ┌───────────────────┐
        │ status: FAILED    │
        └────┬──────────────┘
             │
             ▼
        [Stop chain, return results 1..N]
```

### 7.5 WebSocket Streaming Sequence

```
[Generated via Excalidraw]

Client                          Platform                          Agent
│                                   │                               │
├─ WebSocket Connect ─────────────→ │                               │
│   /ws/SESSION_ID?token=JWT       │                               │
│                                   │ (validate JWT)                │
│                                   ├─ WebSocket Accept ────────────┤
│                                   │                               │
├─ Send Task JSON ────────────────→ │                               │
│   {"message": "...",             │                               │
│    "agent_id": null,             │ Route task                    │
│    "context": {...}}             │                               │
│                                   │ HTTP POST /run ───────────────→│
│                                   │                               │
│ ┌─ Receive {"type": "start"} ────┤ (Task executing)              │
│                                   │                               │
│ ┌─ Receive {"type": "result",  ──┤                  ← Result 200 OK│
│    "content": "..."} ────────────┤ (parse result)                │
│    "tokens_used": 340,           │                               │
│    "cost_usd": 0.001} ───────────┤ (store, track usage)          │
│                                   │                               │
│ ┌─ Receive {"type": "done"} ─────┤                               │
│                                   │                               │
│ (optionally send more tasks      │                               │
│  or close connection)             │                               │
│                                   │                               │
├─ WebSocket Close ───────────────→ │ (cleanup)                    │
│                                   │
```

---

## 8. Security & Compliance

### 8.1 Authentication & Authorization
- **JWT tokens** issued at `/auth/token` after credential validation
- **Token scope:** User identity (sub) and role
- **Enforcement:** Middleware checks Bearer token on protected routes
- **Expiration:** 24 hours (configurable)
- **Production:** Replace dev auth with LDAP, OAuth2, or SAML

### 8.2 Network Security
- **CORS:** Restricted to dashboard URL and localhost (dev)
- **Trusted Hosts:** Only allow requests from whitelisted hosts
- **Security Headers:** HSTS, X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- **WebSocket Auth:** Token must be provided in query params

### 8.3 Input Validation
- **Message size limit:** 10 KB per task message
- **WebSocket payload:** 100 KB limit
- **Credential length:** 255 chars max
- **Agent ID format:** UUID or alphanumeric (validated on registration)

### 8.4 Resource Limits
- **Task timeout:** 300 seconds (5 minutes)
- **Heartbeat timeout:** 90 seconds (agents mark OFFLINE after no ping)
- **Max concurrent requests:** Dependent on FastAPI worker pool
- **Database connections:** Connection pooling (SQLAlchemy)

---

## 9. Scaling & Deployment Considerations

### 9.1 Single Instance (Current)
- ✅ Suitable for < 10 agents, < 1000 tasks/day
- ✅ SQLite database on local disk
- ✅ Minimal operational overhead
- ⚠️ Not HA; no failover

### 9.2 Multi-Instance (Future)
**Requirements for horizontal scaling:**
1. **Shared database** — Migrate from SQLite to PostgreSQL
2. **Distributed registry** — Use Redis for agent heartbeat cache
3. **Message queue** — Kafka/RabbitMQ for async task queuing
4. **Load balancer** — Nginx/HAProxy to distribute requests
5. **Session affinity** — Optional; WebSocket sessions can move across instances

**Migration path:**
```
Single Instance (SQLite)
         ↓
Multi-Instance + PostgreSQL + Redis (no queue)
         ↓
Multi-Instance + PostgreSQL + Redis + Kafka (async)
         ↓
Kubernetes deployment (Helm chart)
```

### 9.3 Observability for Operations
- **Metrics:** Prometheus-compatible endpoint for Grafana
- **Logs:** Structured JSON logs to stdout (for aggregation)
- **Traces:** OpenTelemetry instrumentation (optional)
- **Dashboards:** Show online agents, task success rate, cost per agent

---

## 10. Extension Points

### 10.1 Custom Routing Strategy
Override `route()` in `dispatcher/router.py` to implement:
- ML-based agent selection (ranking model)
- Load-based routing (prefer less busy agents)
- Latency-based routing (prefer fast agents)
- Regional routing (geo-distributed agents)

### 10.2 Custom Storage Backend
Replace SQLAlchemy engine with:
- MongoDB (document storage)
- Cassandra (time-series data)
- DynamoDB (serverless)

### 10.3 Custom Authentication
Replace JWT with:
- OAuth2 + OpenID Connect
- SAML 2.0
- Kerberos/Active Directory

### 10.4 Agent Middleware
Wrap `make_agent_server()` to add:
- Rate limiting per user/role
- Request/response logging
- Custom metrics collection
- Request tracing

---

## 11. Key Metrics & SLOs

| Metric | Target | Notes |
|--------|--------|-------|
| **Task Success Rate** | > 99% | Includes timeouts, agent failures |
| **Agent Availability** | > 99.5% | Uptime of registered agents |
| **Task Latency (P99)** | < 5 sec | Excluding agent execution time |
| **Routing Latency (P99)** | < 100 ms | Time to pick agent (incl. LLM calls) |
| **Platform Uptime** | > 99.9% | Exclude infra failures |
| **Cost per Task** | < $0.01 USD | Token cost + platform overhead |

---

## 12. Appendix: Configuration Reference

### Environment Variables
```
PLATFORM_HOST              (default: 0.0.0.0)
PLATFORM_PORT              (default: 9000)
PLATFORM_ENVIRONMENT       (default: development)
PLATFORM_DEBUG             (default: false)
PLATFORM_SECRET_KEY        (required; change in prod)
PLATFORM_JWT_ALGORITHM     (default: HS256)
PLATFORM_JWT_EXPIRE_MINUTES(default: 1440)
PLATFORM_DB_URL            (default: sqlite:///.../platform.db)
PLATFORM_HEARTBEAT_INTERVAL_S (default: 30)
PLATFORM_HEARTBEAT_TIMEOUT_S  (default: 90)
PLATFORM_ROUTER_MODEL      (default: anthropic/claude-haiku-4-5)
PLATFORM_ANTHROPIC_API_KEY (required for LLM routing)
PLATFORM_DASHBOARD_URL     (default: http://localhost:5173)
PLATFORM_SANDBOX           (default: docker)
PLATFORM_LOG_LEVEL         (default: INFO)
PLATFORM_ENABLE_LOGGING    (default: true)
```

### Database Schema
**platform_agents** table
- `id` (PK): agent identifier
- `name`: human-readable name
- `description`: what agent does
- `capabilities_csv`: comma-separated capability tags
- `version`: semantic version
- `base_url`: HTTP endpoint
- `status`: ONLINE | OFFLINE | BUSY | ERROR
- `registered_at`: when agent joined
- `last_heartbeat`: last ping timestamp
- `metadata_json`: arbitrary agent data

**platform_tasks** table
- `id` (PK): task identifier
- `session_id` (INDEX): groups related tasks
- `agent_id` (INDEX): who executed
- `message`: user input
- `status`: PENDING | RUNNING | COMPLETED | FAILED | CANCELLED
- `result`: agent response
- `tokens_used`, `cost_usd`, `duration_ms`: billing
- `error`: error message if failed
- `context_json`: task context
- `created_at`, `completed_at`: timestamps

**platform_usage** table
- `id` (PK): auto-increment
- `task_id` (INDEX): which task
- `agent_id` (INDEX): which agent
- `tokens_used`, `cost_usd`, `duration_ms`: metrics
- `status`: task result status
- `recorded_at`: timestamp

---

## 13. Glossary

| Term | Definition |
|------|-----------|
| **Agent** | Self-contained AI service that implements AgentBase; registers with platform; receives tasks via HTTP |
| **Task** | A user request + metadata submitted to the platform for execution by an agent |
| **TaskResult** | Response from agent; includes status, content, tokens, cost, duration |
| **Capability** | Well-known tag (code_generation, testing, etc.) that an agent advertises |
| **Routing** | Process of deciding which agent should handle a task |
| **Session** | Logical grouping of related tasks; not persistent on platform |
| **Heartbeat** | Periodic HTTP call from agent to platform to confirm it's online |
| **Artifact** | Output created by agent (file, PR, issue, etc.) tracked in TaskResult |
| **Registry** | Database of agents; source of truth for agent status and capabilities |
| **Executor** | Component that sends tasks to agents and persists results |

---

**Document End**
