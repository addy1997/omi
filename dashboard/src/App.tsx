import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, Layers, ListTodo, BarChart2, Send, Zap, Circle } from "lucide-react";
import AgentsPage from "./pages/Agents";
import TasksPage from "./pages/Tasks";
import ChatPage from "./pages/Chat";
import MetricsPage from "./pages/Metrics";

type Tab = "agents" | "tasks" | "chat" | "metrics";

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "chat",    label: "Chat",    icon: <Send size={16} /> },
  { id: "agents",  label: "Agents",  icon: <Bot size={16} /> },
  { id: "tasks",   label: "Tasks",   icon: <ListTodo size={16} /> },
  { id: "metrics", label: "Metrics", icon: <BarChart2 size={16} /> },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0f1117", color: "#e2e8f0", fontFamily: "'Inter', sans-serif" }}>
      {/* Sidebar */}
      <div style={{ position: "fixed", top: 0, left: 0, bottom: 0, width: 220,
        backgroundColor: "#161b27", borderRight: "1px solid #1e2535",
        display: "flex", flexDirection: "column", padding: "1.5rem 0" }}>

        {/* Logo */}
        <div style={{ padding: "0 1.5rem 1.5rem", borderBottom: "1px solid #1e2535" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <div style={{ width: 32, height: 32, borderRadius: "0.5rem",
              background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
              display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Zap size={18} color="#fff" />
            </div>
            <div>
              <p style={{ fontWeight: 700, fontSize: "0.95rem", margin: 0,
                fontFamily: "'Space Grotesk', sans-serif", letterSpacing: "-0.02em" }}>Omi</p>
              <p style={{ fontSize: "0.65rem", color: "#64748b", margin: 0 }}>Multi-Agent Platform</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: "1rem 0.75rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{
                display: "flex", alignItems: "center", gap: "0.65rem",
                padding: "0.55rem 0.85rem", borderRadius: "0.5rem",
                border: "none", cursor: "pointer", textAlign: "left", width: "100%",
                fontSize: "0.83rem", fontWeight: tab === t.id ? 600 : 400,
                backgroundColor: tab === t.id ? "rgba(59,130,246,0.12)" : "transparent",
                color: tab === t.id ? "#3b82f6" : "#94a3b8",
                transition: "all 0.15s ease",
              }}>
              {t.icon} {t.label}
            </button>
          ))}
        </nav>

        {/* Status dot */}
        <div style={{ padding: "1rem 1.5rem", borderTop: "1px solid #1e2535",
          display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Circle size={8} fill="#10b981" color="#10b981" />
          <span style={{ fontSize: "0.72rem", color: "#64748b" }}>Platform online</span>
        </div>
      </div>

      {/* Main */}
      <div style={{ marginLeft: 220, padding: "2rem", minHeight: "100vh" }}>
        <AnimatePresence mode="wait">
          <motion.div key={tab}
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
            {tab === "chat"    && <ChatPage />}
            {tab === "agents"  && <AgentsPage />}
            {tab === "tasks"   && <TasksPage />}
            {tab === "metrics" && <MetricsPage />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
