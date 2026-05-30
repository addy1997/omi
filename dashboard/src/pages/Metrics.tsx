import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { BarChart2, Zap, DollarSign, Clock, RefreshCw } from "lucide-react";
import { api, type UsageSummary } from "../api";

interface PerAgent { agent_id: string; tasks: number; tokens: number; cost_usd: number; }

function StatCard({ icon, label, value, sub }: {
  icon: React.ReactNode; label: string; value: string; sub?: string;
}) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      style={{ backgroundColor: "#161b27", border: "1px solid #1e2535",
        borderRadius: "0.875rem", padding: "1.5rem",
        display: "flex", alignItems: "center", gap: "1rem" }}>
      <div style={{ width: 44, height: 44, borderRadius: "0.6rem",
        background: "linear-gradient(135deg, #1e2535, #2d3748)",
        display: "flex", alignItems: "center", justifyContent: "center",
        border: "1px solid #2d3748", flexShrink: 0 }}>
        {icon}
      </div>
      <div>
        <p style={{ margin: 0, fontSize: "0.72rem", color: "#64748b", fontWeight: 500 }}>{label}</p>
        <p style={{ margin: 0, fontSize: "1.5rem", fontWeight: 700,
          fontFamily: "'Space Grotesk', sans-serif", lineHeight: 1.2 }}>{value}</p>
        {sub && <p style={{ margin: 0, fontSize: "0.68rem", color: "#475569" }}>{sub}</p>}
      </div>
    </motion.div>
  );
}

function AgentBar({ entry, maxTasks }: { entry: PerAgent; maxTasks: number }) {
  const pct = maxTasks > 0 ? (entry.tasks / maxTasks) * 100 : 0;
  return (
    <div style={{ marginBottom: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between",
        marginBottom: "0.35rem", fontSize: "0.78rem" }}>
        <span style={{ fontWeight: 600 }}>{entry.agent_id}</span>
        <span style={{ color: "#64748b" }}>{entry.tasks} tasks · ${entry.cost_usd.toFixed(4)}</span>
      </div>
      <div style={{ height: 8, backgroundColor: "#1e2535", borderRadius: "999px", overflow: "hidden" }}>
        <motion.div
          initial={{ width: 0 }} animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          style={{ height: "100%", borderRadius: "999px",
            background: "linear-gradient(90deg, #3b82f6, #8b5cf6)" }} />
      </div>
    </div>
  );
}

export default function MetricsPage() {
  const [summary, setSummary]   = useState<UsageSummary | null>(null);
  const [perAgent, setPerAgent] = useState<PerAgent[]>([]);
  const [loading, setLoading]   = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [s, p] = await Promise.all([api.usage(), api.perAgent()]);
      setSummary(s); setPerAgent(p);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const maxTasks = Math.max(...perAgent.map(a => a.tasks), 1);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "2rem" }}>
        <div>
          <p style={{ fontSize: "0.75rem", fontWeight: 600, letterSpacing: "0.1em",
            textTransform: "uppercase", color: "#3b82f6", marginBottom: "0.3rem" }}>Observability</p>
          <h1 style={{ margin: 0, fontSize: "1.75rem", fontWeight: 700,
            fontFamily: "'Space Grotesk', sans-serif", letterSpacing: "-0.02em" }}>Metrics</h1>
        </div>
        <button onClick={load} style={{ background: "none", border: "1px solid #1e2535",
          borderRadius: "0.5rem", padding: "0.5rem", cursor: "pointer", color: "#64748b",
          display: "flex", alignItems: "center" }}>
          <RefreshCw size={16} />
        </button>
      </div>

      {loading ? (
        <div style={{ color: "#475569", textAlign: "center", padding: "3rem" }}>Loading…</div>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px,1fr))",
            gap: "1rem", marginBottom: "2rem" }}>
            <StatCard icon={<Zap size={20} color="#3b82f6" />}
              label="Total Tasks" value={String(summary?.total_tasks ?? 0)} />
            <StatCard icon={<BarChart2 size={20} color="#8b5cf6" />}
              label="Total Tokens" value={(summary?.total_tokens ?? 0).toLocaleString()} />
            <StatCard icon={<DollarSign size={20} color="#10b981" />}
              label="Total Cost" value={`$${(summary?.total_cost_usd ?? 0).toFixed(4)}`}
              sub="across all agents" />
            <StatCard icon={<Clock size={20} color="#f59e0b" />}
              label="Avg Duration" value={`${summary?.avg_duration_ms ?? 0}ms`}
              sub="per task" />
          </div>

          {perAgent.length > 0 && (
            <div style={{ backgroundColor: "#161b27", border: "1px solid #1e2535",
              borderRadius: "0.875rem", padding: "1.5rem" }}>
              <h3 style={{ margin: "0 0 1.5rem", fontSize: "0.9rem", fontWeight: 700,
                fontFamily: "'Space Grotesk', sans-serif" }}>Usage per agent</h3>
              {perAgent.map(a => <AgentBar key={a.agent_id} entry={a} maxTasks={maxTasks} />)}
            </div>
          )}

          {perAgent.length === 0 && (
            <div style={{ textAlign: "center", padding: "3rem", color: "#475569" }}>
              <BarChart2 size={40} style={{ margin: "0 auto 1rem", opacity: 0.3 }} />
              <p>No usage data yet. Submit some tasks to see metrics here.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
