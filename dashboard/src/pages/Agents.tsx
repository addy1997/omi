import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Bot, RefreshCw, Circle, Zap } from "lucide-react";
import { api, type AgentInfo } from "../api";

const STATUS_COLOR: Record<string, string> = {
  online:  "#10b981",
  offline: "#64748b",
  busy:    "#f59e0b",
  error:   "#ef4444",
};

const CAP_COLOR: Record<string, string> = {
  code_generation: "#3b82f6",
  code_review:     "#8b5cf6",
  code_search:     "#06b6d4",
  planning:        "#f59e0b",
  issue_triage:    "#ec4899",
  web_research:    "#10b981",
  data_analysis:   "#f97316",
  devops:          "#64748b",
  testing:         "#a855f7",
  general:         "#94a3b8",
};

function AgentCard({ agent }: { agent: AgentInfo }) {
  const color = STATUS_COLOR[agent.status] ?? "#64748b";
  const lastSeen = new Date(agent.last_heartbeat).toLocaleTimeString();

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      style={{
        backgroundColor: "#161b27", border: "1px solid #1e2535",
        borderRadius: "0.875rem", padding: "1.5rem",
        display: "flex", flexDirection: "column", gap: "1rem",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{ width: 40, height: 40, borderRadius: "0.6rem",
            background: "linear-gradient(135deg, #1e2535, #2d3748)",
            display: "flex", alignItems: "center", justifyContent: "center",
            border: `1px solid ${color}33` }}>
            <Bot size={20} color={color} />
          </div>
          <div>
            <p style={{ margin: 0, fontWeight: 700, fontSize: "0.95rem",
              fontFamily: "'Space Grotesk', sans-serif" }}>{agent.name}</p>
            <p style={{ margin: 0, fontSize: "0.7rem", color: "#64748b" }}>v{agent.version}</p>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem",
          padding: "0.25rem 0.65rem", borderRadius: "999px",
          backgroundColor: `${color}18`, border: `1px solid ${color}33` }}>
          <Circle size={7} fill={color} color={color} />
          <span style={{ fontSize: "0.7rem", fontWeight: 600, color }}>{agent.status}</span>
        </div>
      </div>

      <p style={{ margin: 0, fontSize: "0.8rem", color: "#94a3b8", lineHeight: 1.6 }}>
        {agent.description}
      </p>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
        {agent.capabilities.map(cap => (
          <span key={cap} style={{
            fontSize: "0.68rem", fontWeight: 500,
            padding: "0.2rem 0.55rem", borderRadius: "999px",
            backgroundColor: `${CAP_COLOR[cap] ?? "#94a3b8"}18`,
            color: CAP_COLOR[cap] ?? "#94a3b8",
            border: `1px solid ${CAP_COLOR[cap] ?? "#94a3b8"}30`,
          }}>{cap.replace("_", " ")}</span>
        ))}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between",
        fontSize: "0.68rem", color: "#475569", borderTop: "1px solid #1e2535", paddingTop: "0.75rem" }}>
        <span>ID: {agent.id}</span>
        <span>Last seen: {lastSeen}</span>
      </div>
    </motion.div>
  );
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try { setAgents(await api.agents()); } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const online  = agents.filter(a => a.status === "online").length;
  const offline = agents.filter(a => a.status === "offline").length;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "2rem" }}>
        <div>
          <p style={{ fontSize: "0.75rem", fontWeight: 600, letterSpacing: "0.1em",
            textTransform: "uppercase", color: "#3b82f6", marginBottom: "0.3rem" }}>Registry</p>
          <h1 style={{ margin: 0, fontSize: "1.75rem", fontWeight: 700,
            fontFamily: "'Space Grotesk', sans-serif", letterSpacing: "-0.02em" }}>Agents</h1>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            {[{ label: "Online", val: online, c: "#10b981" },
              { label: "Offline", val: offline, c: "#64748b" }].map(s => (
              <div key={s.label} style={{ textAlign: "center" }}>
                <p style={{ margin: 0, fontSize: "1.4rem", fontWeight: 700, color: s.c }}>{s.val}</p>
                <p style={{ margin: 0, fontSize: "0.68rem", color: "#64748b" }}>{s.label}</p>
              </div>
            ))}
          </div>
          <button onClick={load} style={{ background: "none", border: "1px solid #1e2535",
            borderRadius: "0.5rem", padding: "0.5rem", cursor: "pointer", color: "#64748b",
            display: "flex", alignItems: "center" }}>
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1rem" }}>
          {[1,2,3].map(i => (
            <div key={i} style={{ backgroundColor: "#161b27", border: "1px solid #1e2535",
              borderRadius: "0.875rem", height: 220, opacity: 0.4 }} />
          ))}
        </div>
      ) : agents.length === 0 ? (
        <div style={{ textAlign: "center", padding: "4rem", color: "#475569" }}>
          <Bot size={48} style={{ margin: "0 auto 1rem", opacity: 0.3 }} />
          <p style={{ fontWeight: 600 }}>No agents registered</p>
          <p style={{ fontSize: "0.8rem" }}>Start an agent and it will appear here automatically.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1rem" }}>
          {agents.map(a => <AgentCard key={a.id} agent={a} />)}
        </div>
      )}
    </div>
  );
}
