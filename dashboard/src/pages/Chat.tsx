import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User, Zap, ChevronDown, Download } from "lucide-react";
import { api, createWS, type AgentInfo } from "../api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent_id?: string;
  tokens?: number;
  cost?: number;
  duration_ms?: number;
  status?: string;
}

function ChartViewer({ html }: { html: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  const downloadChart = () => {
    const link = document.createElement("a");
    link.href = `data:text/html;charset=utf-8,${encodeURIComponent(html)}`;
    link.download = `chart-${Date.now()}.html`;
    link.click();
  };

  return (
    <div style={{
      backgroundColor: "#161b27",
      borderRadius: "0.6rem",
      border: "1px solid #1e2535",
      padding: "0.75rem",
      marginTop: "0.5rem"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
        <span style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 600 }}>Plotly Chart</span>
        <button onClick={downloadChart}
          style={{
            display: "flex", alignItems: "center", gap: "0.3rem",
            padding: "0.25rem 0.5rem",
            backgroundColor: "#3b82f6",
            color: "#fff",
            border: "none",
            borderRadius: "0.3rem",
            fontSize: "0.7rem",
            cursor: "pointer"
          }}>
          <Download size={12} /> Download
        </button>
      </div>
      <div ref={containerRef}
        style={{
          backgroundColor: "#0f1117",
          borderRadius: "0.4rem",
          border: "1px solid #1e2535",
          minHeight: "400px",
          maxHeight: "600px",
          overflow: "auto"
        }}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}

function Bubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  const isChart = !isUser && msg.content.includes("<div id=\"chart");

  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.22 }}
      style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: "1rem", gap: "0.6rem", alignItems: isChart ? "flex-start" : "flex-end" }}>
      {!isUser && (
        <div style={{ width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
          background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
          display: "flex", alignItems: "center", justifyContent: "center", marginTop: isChart ? "0.5rem" : 0 }}>
          <Bot size={14} color="#fff" />
        </div>
      )}
      <div style={{ maxWidth: isChart ? "90%" : "75%" }}>
        {isChart ? (
          <ChartViewer html={msg.content} />
        ) : (
          <div style={{
            padding: "0.65rem 1rem",
            borderRadius: isUser ? "1rem 1rem 0.15rem 1rem" : "1rem 1rem 1rem 0.15rem",
            backgroundColor: isUser ? "#3b82f6" : "#1e2535",
            color: isUser ? "#fff" : "#e2e8f0",
            fontSize: "0.85rem", lineHeight: 1.65, whiteSpace: "pre-wrap",
          }}>
            {msg.content}
          </div>
        )}
        {!isUser && msg.agent_id && (
          <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.35rem",
            fontSize: "0.65rem", color: "#475569", paddingLeft: "0.25rem" }}>
            <span>{msg.agent_id}</span>
            {msg.tokens && <span>{msg.tokens} tokens</span>}
            {msg.cost && <span>${msg.cost.toFixed(5)}</span>}
            {msg.duration_ms && <span>{msg.duration_ms}ms</span>}
          </div>
        )}
      </div>
      {isUser && (
        <div style={{ width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
          backgroundColor: "#1e2535", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <User size={14} color="#94a3b8" />
        </div>
      )}
    </motion.div>
  );
}

function TypingDots() {
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: "0.6rem", marginBottom: "1rem" }}>
      <div style={{ width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
        background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
        display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Bot size={14} color="#fff" />
      </div>
      <div style={{ padding: "0.65rem 1rem", borderRadius: "1rem 1rem 1rem 0.15rem",
        backgroundColor: "#1e2535", display: "flex", gap: "4px", alignItems: "center" }}>
        {[0,1,2].map(i => (
          <motion.span key={i}
            animate={{ y: [0, -4, 0] }}
            transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
            style={{ width: 6, height: 6, borderRadius: "50%",
              backgroundColor: "#3b82f6", display: "block" }} />
        ))}
      </div>
    </div>
  );
}

const SUGGESTED = [
  "Review the Omi codebase and summarise its architecture",
  "Plan a feature: add rate limiting to the platform API",
  "Search for how to implement pgvector semantic search",
  "Triage the open GitHub issues for addy1997/omi",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);
  const [agents, setAgents]     = useState<AgentInfo[]>([]);
  const [agentId, setAgentId]   = useState<string>("");
  const [sessionId]             = useState(crypto.randomUUID());
  const bottomRef               = useRef<HTMLDivElement>(null);
  const wsRef                   = useRef<WebSocket | null>(null);

  useEffect(() => {
    api.agents().then(setAgents).catch(() => {});
    wsRef.current = createWS(sessionId, handleWsMessage);
    return () => wsRef.current?.close();
  }, []);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  const handleWsMessage = (msg: unknown) => {
    const m = msg as Record<string, unknown>;
    if (m.type === "result") {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: m.content as string,
        agent_id: m.agent_id as string,
        tokens: m.tokens_used as number,
        cost: m.cost_usd as number,
        duration_ms: m.duration_ms as number,
        status: m.status as string,
      }]);
      setLoading(false);
    } else if (m.type === "error") {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(), role: "assistant",
        content: `Error: ${m.content}`,
      }]);
      setLoading(false);
    }
  };

  const send = (text: string) => {
    const t = text.trim();
    if (!t || loading) return;
    setInput("");
    setMessages(prev => [...prev, { id: crypto.randomUUID(), role: "user", content: t }]);
    setLoading(true);

    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ message: t, agent_id: agentId || null }));
    } else {
      api.submitTask(t, agentId || undefined)
        .then((r: unknown) => {
          const res = r as Record<string, unknown>;
          setMessages(prev => [...prev, {
            id: crypto.randomUUID(), role: "assistant",
            content: (res.content as string) || "No response.",
            agent_id: res.agent_id as string,
            tokens: res.tokens_used as number,
            cost: res.cost_usd as number,
            duration_ms: res.duration_ms as number,
          }]);
        })
        .catch(e => setMessages(prev => [...prev, {
          id: crypto.randomUUID(), role: "assistant", content: `Error: ${e.message}`,
        }]))
        .finally(() => setLoading(false));
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 4rem)", maxWidth: 860, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem", flexShrink: 0 }}>
        <div>
          <p style={{ fontSize: "0.75rem", fontWeight: 600, letterSpacing: "0.1em",
            textTransform: "uppercase", color: "#3b82f6", marginBottom: "0.3rem" }}>Platform</p>
          <h1 style={{ margin: 0, fontSize: "1.75rem", fontWeight: 700,
            fontFamily: "'Space Grotesk', sans-serif", letterSpacing: "-0.02em" }}>Chat</h1>
        </div>

        {/* Agent selector */}
        <div style={{ position: "relative" }}>
          <select value={agentId} onChange={e => setAgentId(e.target.value)}
            style={{ appearance: "none", backgroundColor: "#161b27", border: "1px solid #1e2535",
              borderRadius: "0.5rem", padding: "0.5rem 2rem 0.5rem 0.75rem",
              color: "#e2e8f0", fontSize: "0.8rem", cursor: "pointer", outline: "none" }}>
            <option value="">Auto-route</option>
            {agents.filter(a => a.status === "online").map(a => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
          <ChevronDown size={12} style={{ position: "absolute", right: "0.5rem", top: "50%",
            transform: "translateY(-50%)", color: "#64748b", pointerEvents: "none" }} />
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", paddingRight: "0.5rem" }}>
        {messages.length === 0 && !loading && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center",
            justifyContent: "center", height: "100%", gap: "1.5rem" }}>
            <div style={{ width: 56, height: 56, borderRadius: "1rem",
              background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
              display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Zap size={28} color="#fff" />
            </div>
            <div style={{ textAlign: "center" }}>
              <p style={{ fontWeight: 700, fontSize: "1.1rem", fontFamily: "'Space Grotesk', sans-serif" }}>
                What can Omi help with?
              </p>
              <p style={{ color: "#64748b", fontSize: "0.82rem" }}>
                Tasks are routed to the best available agent automatically.
              </p>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", width: "100%", maxWidth: 560 }}>
              {SUGGESTED.map(s => (
                <button key={s} onClick={() => send(s)}
                  style={{ textAlign: "left", backgroundColor: "#161b27", border: "1px solid #1e2535",
                    borderRadius: "0.6rem", padding: "0.75rem 1rem", cursor: "pointer",
                    color: "#94a3b8", fontSize: "0.78rem", lineHeight: 1.5,
                    transition: "border-color 0.15s" }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = "#3b82f6")}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = "#1e2535")}
                >{s}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map(m => <Bubble key={m.id} msg={m} />)}
        {loading && <TypingDots />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ flexShrink: 0, paddingTop: "1rem", display: "flex", gap: "0.5rem" }}>
        <input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
          placeholder="Ask anything — platform routes to the right agent…"
          disabled={loading}
          style={{ flex: 1, backgroundColor: "#161b27", border: "1px solid #1e2535",
            borderRadius: "0.6rem", padding: "0.7rem 1rem", color: "#e2e8f0",
            fontSize: "0.875rem", outline: "none" }}
          onFocus={e => (e.currentTarget.style.borderColor = "#3b82f6")}
          onBlur={e => (e.currentTarget.style.borderColor = "#1e2535")} />
        <button onClick={() => send(input)} disabled={loading || !input.trim()}
          style={{ width: 42, height: 42, borderRadius: "0.5rem", border: "none", flexShrink: 0,
            backgroundColor: input.trim() && !loading ? "#3b82f6" : "#1e2535",
            color: input.trim() && !loading ? "#fff" : "#475569",
            cursor: input.trim() && !loading ? "pointer" : "not-allowed",
            display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
