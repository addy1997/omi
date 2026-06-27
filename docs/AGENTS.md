# Omi Agents

The Omi platform includes 5 specialist agents, each optimized for a specific domain. New agents can be added by implementing the AgentBase interface from the platform SDK.

## Agent Directory

### 1. **Helix** — Coding Agent
**Port:** 8000  
**Specialization:** Code generation, testing, refactoring, version control  
**Status:** ✅ Fully implemented

**Capabilities:**
- Write, edit, test code across multiple languages
- Git operations (worktrees, commits, PRs)
- GitHub integration (issues, PRs, code search)
- AST-aware symbol lookup (Tree-sitter)
- Shell execution with Docker sandbox
- Surgical code edits with rollback on failure

**Tools:** File I/O, Git, GitHub API, Shell, Tree-sitter AST

**Example Task:**
```
"Implement user authentication with JWT in FastAPI"
→ Helix explores codebase
→ Plans changes
→ Creates worktree (omi/auth-jwt)
→ Edits files, runs tests
→ Creates PR
```

---

### 2. **Nexus** — DevOps Agent
**Port:** 8001  
**Specialization:** Infrastructure, deployments, Kubernetes, cloud ops  
**Status:** 🚧 Foundation built, implementation in progress

**Planned Capabilities:**
- Deploy to AWS, GCP, Azure
- Kubernetes cluster management
- Docker image building & pushing
- Infrastructure as Code (Terraform, CloudFormation)
- Monitoring & alerting (Prometheus, Grafana, DataDog)
- Incident response & auto-remediation
- Log aggregation & analysis
- Scaling & performance optimization
- CI/CD pipeline setup

**Planned Tools:**
- Docker API, Kubernetes Python client
- Boto3 (AWS), google-cloud, azure-sdk
- SSH/Paramiko for remote execution
- Terraform, CloudFormation parsers
- Prometheus/Grafana query APIs

**Example Task:**
```
"Deploy the Omi platform to Kubernetes with auto-scaling"
→ Nexus generates K8s manifests
→ Sets up Prometheus monitoring
→ Configures ingress & scaling policies
→ Performs health checks
→ Reports deployment status
```

---

### 3. **Flux** — Data Agent
**Port:** 8002  
**Specialization:** Data analysis, SQL, analytics, BI  
**Status:** 🚧 Foundation built, implementation in progress

**Planned Capabilities:**
- SQL generation and execution (PostgreSQL, DuckDB, BigQuery)
- Data exploration & profiling
- Statistical analysis & correlation detection
- Chart & dashboard generation (Plotly)
- Data pipeline construction
- ETL workflow automation
- CSV/Parquet file analysis
- Query optimization suggestions
- Integration with BI tools (Tableau, Looker, Metabase)

**Planned Tools:**
- SQLAlchemy for database ops
- DuckDB for file analysis
- Pandas for data manipulation
- Plotly for visualization
- Jupyter notebook integration

**Example Task:**
```
"Analyze user churn patterns in the database and create a dashboard"
→ Flux queries user data
→ Performs cohort analysis
→ Detects churn signals
→ Generates visualizations
→ Creates interactive dashboard
```

---

### 4. **Planner** — Planning Agent
**Port:** (runs via platform)  
**Specialization:** Feature decomposition, roadmaps, issue creation  
**Status:** ✅ Fully implemented

**Capabilities:**
- Break features into GitHub issues
- Estimate story points
- Order by dependencies
- Create sprint plans
- Generate roadmaps

---

### 5. **Researcher** — Research Agent
**Port:** (runs via platform)  
**Specialization:** Web search, documentation, API learning  
**Status:** ✅ Fully implemented

**Capabilities:**
- Web search (DuckDuckGo)
- URL fetching & summarization
- Documentation lookup
- Error investigation
- Best practices research

---

### 6. **Triager** — Issue Triage Agent
**Port:** (runs via platform)  
**Specialization:** Issue management, labeling, backlog grooming  
**Status:** ✅ Fully implemented

**Capabilities:**
- Categorize issues (bug, feature, question, etc.)
- Auto-label based on content
- Duplicate detection
- Priority assignment
- Backlog organization

---

## Building a New Agent

To create a new agent for Omi:

### 1. Use the Agent SDK
```python
from omi_platform.sdk.agent_base import AgentBase, Capability, Task, TaskResult

class MyAgent(AgentBase):
    name = "my-agent"
    description = "Does specific work"
    capabilities = [Capability.CODE_GENERATION, Capability.TESTING]
    version = "0.1.0"
    
    async def handle(self, task: Task) -> TaskResult:
        # Implement your logic
        return TaskResult(
            task_id=task.id,
            agent_id=self.agent_id,
            content="Result"
        )
```

### 2. Implement Tools
```python
from omi_platform.sdk.agent_base import make_agent_server

agent = MyAgent(base_url="http://localhost:8003")
app = make_agent_server(agent)
```

### 3. Register with Platform
```bash
# Start your agent
python -m myagent.cli serve --port 8003

# Platform auto-discovers it via heartbeat
# Agent appears in dashboard within 30 seconds
```

### 4. Extend Platform Router
Add capability keywords in `platform/omi_platform/dispatcher/router.py` for auto-routing:

```python
_KEYWORD_MAP["my_capability"] = ["keyword1", "keyword2"]
```

---

## Agent Communication

Agents communicate **only** through the platform:

```
User → Platform API → Router → Agent → Platform → Return to User
```

- Each agent is **stateless** (state stored in platform DB)
- Agents can **call each other** via platform (Planner → Coder → Researcher chains)
- **No direct agent-to-agent calls** (loose coupling)

---

## Roadmap

### Phase 1 (Current)
- ✅ Helix (Coder)
- ✅ Planner, Researcher, Triager
- 🚧 Nexus (DevOps - foundation)
- 🚧 Flux (Data - foundation)

### Phase 2 (Planned)
- Vision agent (image analysis, design review)
- Analytics agent (business metrics, dashboards)
- Security agent (vulnerability scanning, compliance)

### Phase 3 (Future)
- Custom agent builder (no-code agent creation)
- Agent marketplace (publish & discover agents)
- Agent swarms (multi-agent collaboration on complex tasks)

---

## Testing Agents

### Local Testing
```bash
# Test Helix
cd agents/helix
helix chat

# Test Nexus (when ready)
cd agents/nexus
nexus chat

# Test Flux (when ready)
cd agents/flux
flux chat
```

### Integration Testing
```bash
# Start platform
omi-platform serve

# Start agents
helix serve-agent --platform http://localhost:9000
nexus serve-agent --platform http://localhost:9000  # Coming soon
flux serve-agent --platform http://localhost:9000   # Coming soon

# Submit tasks via dashboard
# http://localhost:5173
```

---

## Contributing

To contribute a new agent:

1. **Fork** the repository
2. **Create** `agents/your-agent/` following Helix structure
3. **Implement** the AgentBase interface
4. **Test** locally with platform
5. **Submit PR** with documentation

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
