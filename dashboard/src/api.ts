const BASE = import.meta.env.VITE_PLATFORM_URL ?? "http://localhost:9000";

export interface AgentInfo {
  id: string; name: string; description: string;
  capabilities: string[]; version: string; base_url: string;
  status: "online" | "offline" | "busy" | "error";
  registered_at: string; last_heartbeat: string;
}

export interface TaskRecord {
  id: string; session_id: string; agent_id: string | null;
  message: string; status: string; result: string | null;
  tokens_used: number; cost_usd: number; duration_ms: number;
  error: string | null; created_at: string; completed_at: string | null;
}

export interface UsageSummary {
  total_tasks: number; total_tokens: number;
  total_cost_usd: number; avg_duration_ms: number;
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export const api = {
  health:      () => get<{ status: string; online_agents: number; agents: AgentInfo[] }>("/health"),
  agents:      () => get<AgentInfo[]>("/agents"),
  tasks:       (limit = 50) => get<TaskRecord[]>(`/tasks?limit=${limit}`),
  usage:       () => get<UsageSummary>("/tasks/usage/summary"),
  perAgent:    () => get<{ agent_id: string; tasks: number; tokens: number; cost_usd: number }[]>("/tasks/usage/per-agent"),
  submitTask:  (message: string, agentId?: string) =>
    post("/tasks", { message, agent_id: agentId ?? null, session_id: crypto.randomUUID() }),
};

export function createWS(sessionId: string, onMessage: (msg: unknown) => void) {
  const wsBase = BASE.replace(/^http/, "ws");
  const ws = new WebSocket(`${wsBase}/ws/${sessionId}`);
  ws.onmessage = (e) => onMessage(JSON.parse(e.data));
  return ws;
}
