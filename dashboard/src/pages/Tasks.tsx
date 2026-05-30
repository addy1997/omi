import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ListTodo, RefreshCw, CheckCircle, XCircle, Clock, Loader } from "lucide-react";
import { api, type TaskRecord } from "../api";

const STATUS_ICON: Record<string, React.ReactNode> = {
  completed: <CheckCircle size={14} color="#10b981" />,
  failed:    <XCircle size={14} color="#ef4444" />,
  pending:   <Clock size={14} color="#f59e0b" />,
  running:   <Loader size={14} color="#3b82f6" />,
};

function TaskRow({ task }: { task: TaskRecord }) {
  const [expanded, setExpanded] = useState(false);
  const created = new Date(task.created_at).toLocaleString();

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      style={{ backgroundColor: "#161b27", border: "1px solid #1e2535",
        borderRadius: "0.75rem", overflow: "hidden", marginBottom: "0.5rem" }}>
      <div onClick={() => setExpanded(v => !v)}
        style={{ padding: "1rem 1.25rem", cursor: "pointer", display: "flex",
          alignItems: "center", gap: "0.75rem" }}>
        <span style={{ flexShrink: 0 }}>{STATUS_ICON[task.status] ?? STATUS_ICON.pending}</span>
        <p style={{ margin: 0, flex: 1, fontSize: "0.83rem", color: "#e2e8f0",
          whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {task.message}
        </p>
        <div style={{ display: "flex", gap: "1.25rem", flexShrink: 0, fontSize: "0.7rem", color: "#475569" }}>
          {task.agent_id && <span>{task.agent_id}</span>}
          {task.tokens_used > 0 && <span>{task.tokens_used} tk</span>}
          {task.duration_ms > 0 && <span>{task.duration_ms}ms</span>}
          <span>{created}</span>
        </div>
      </div>

      {expanded && (
        <motion.div initial={{ height: 0 }} animate={{ height: "auto" }}
          style={{ borderTop: "1px solid #1e2535", padding: "1rem 1.25rem",
            fontSize: "0.8rem", color: "#94a3b8" }}>
          {task.result ? (
            <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word",
              fontFamily: "monospace", lineHeight: 1.6 }}>{task.result}</pre>
          ) : task.error ? (
            <p style={{ margin: 0, color: "#ef4444" }}>Error: {task.error}</p>
          ) : (
            <p style={{ margin: 0, color: "#475569" }}>No result yet.</p>
          )}
          <div style={{ marginTop: "0.75rem", display: "flex", gap: "1rem",
            fontSize: "0.68rem", color: "#475569", borderTop: "1px solid #1e2535", paddingTop: "0.75rem" }}>
            <span>ID: {task.id}</span>
            <span>Session: {task.session_id}</span>
            {task.cost_usd > 0 && <span>Cost: ${task.cost_usd.toFixed(5)}</span>}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}

export default function TasksPage() {
  const [tasks, setTasks]   = useState<TaskRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter]   = useState<string>("all");

  const load = async () => {
    setLoading(true);
    try { setTasks(await api.tasks()); } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const displayed = filter === "all" ? tasks : tasks.filter(t => t.status === filter);

  const counts: Record<string, number> = tasks.reduce((acc, t) => {
    acc[t.status] = (acc[t.status] ?? 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <div>
          <p style={{ fontSize: "0.75rem", fontWeight: 600, letterSpacing: "0.1em",
            textTransform: "uppercase", color: "#3b82f6", marginBottom: "0.3rem" }}>History</p>
          <h1 style={{ margin: 0, fontSize: "1.75rem", fontWeight: 700,
            fontFamily: "'Space Grotesk', sans-serif", letterSpacing: "-0.02em" }}>Tasks</h1>
        </div>
        <button onClick={load} style={{ background: "none", border: "1px solid #1e2535",
          borderRadius: "0.5rem", padding: "0.5rem", cursor: "pointer", color: "#64748b",
          display: "flex", alignItems: "center" }}>
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem" }}>
        {["all", "completed", "failed", "pending", "running"].map(s => (
          <button key={s} onClick={() => setFilter(s)}
            style={{ padding: "0.3rem 0.75rem", borderRadius: "999px", border: "1px solid",
              fontSize: "0.75rem", fontWeight: 500, cursor: "pointer",
              borderColor: filter === s ? "#3b82f6" : "#1e2535",
              backgroundColor: filter === s ? "rgba(59,130,246,0.12)" : "transparent",
              color: filter === s ? "#3b82f6" : "#64748b" }}>
            {s} {s !== "all" && counts[s] ? `(${counts[s]})` : ""}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ color: "#475569", textAlign: "center", padding: "3rem" }}>Loading…</div>
      ) : displayed.length === 0 ? (
        <div style={{ textAlign: "center", padding: "4rem", color: "#475569" }}>
          <ListTodo size={40} style={{ margin: "0 auto 1rem", opacity: 0.3 }} />
          <p>No tasks found.</p>
        </div>
      ) : (
        displayed.map(t => <TaskRow key={t.id} task={t} />)
      )}
    </div>
  );
}
