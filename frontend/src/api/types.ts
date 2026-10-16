export type Decision = 'allow' | 'block' | 'ask';
export type Tool = 'shell' | 'file' | 'http';
export type Source = 'gate' | 'squid' | 'dnsmasq' | 'seccomp' | 'cgroup' | 'inspector';

export interface WsEnvelope<T extends string, D> {
  v: 1;
  seq: number;          // monotonically increasing, used to resume after reconnect
  ts: string;           // ISO 8601
  type: T;
  data: D;
}

export interface AuditEntry {
  id: number;
  ts: string;
  session_id: string;
  task_id: string | null;
  source: Source;
  tool: Tool;
  args: string;               // already truncated and redacted by the server
  decision: Decision;
  reason: string;
  rule_id: string;            // e.g. "NET-004"
  risk_score: number | null;  // 0.00 to 1.00 (Prompt Guard 2 + rules)
  user_input?: string;
  agent_thought?: string;
  container_id: string | null;
  policy_hash: string;
  hash: string;
  prev_hash: string;
}

export interface AgentMessage {
  id?: string;
  ts?: string;
  role: 'user' | 'agent';
  text: string;
  tool_call_id?: string;
}

export interface ToolResult {
  audit_id: number;
  ok: boolean;
  summary: string;
  exit_code?: number;
}

export interface AskRequest {
  audit_id: number;
  tool: Tool;
  args: string;
  reason: string;
  risk_score: number;
  expires_at: string;
}

export interface NetworkEvent {
  ts?: string;
  type: 'HTTP' | 'DNS';
  target: string;
  action: 'allow' | 'block';
  rule_id: string;
}

export interface ResourceUsage {
  cpu_pct: number;
  mem_mb: number;
  mem_limit_mb: number;
  disk_mb: number;
  disk_limit_mb: number;
  pids: number;
  pids_limit: number;
}

export interface ScenarioItem {
  id: string;
  name: string;
  kind: 'attack' | 'normal';
  description: string;
  target_rule?: string;
  status: 'idle' | 'running' | 'blocked' | 'done' | 'failed';
  outcome?: string;
  last_run?: string;
}

export interface ChainStatus {
  ok: boolean;
  entries: number;
  head_hash: string;
  last_verified: string;
  first_broken_id?: number;
}

export interface SystemStatusData {
  sandbox: 'on' | 'off';
  components: Record<string, 'running' | 'active' | 'logging' | 'connected' | 'down'>;
  uptime_s: number;
}

export type LiveEvent =
  | WsEnvelope<'audit', AuditEntry>
  | WsEnvelope<'agent_message', AgentMessage>
  | WsEnvelope<'tool_result', ToolResult>
  | WsEnvelope<'ask_request', AskRequest>
  | WsEnvelope<'ask_resolved', { audit_id: number; outcome: 'approved' | 'denied' | 'timeout' }>
  | WsEnvelope<'network', NetworkEvent>
  | WsEnvelope<'resources', ResourceUsage>
  | WsEnvelope<'scenario', { id: string; kind: 'attack' | 'normal'; status: 'idle' | 'running' | 'blocked' | 'done' | 'failed'; outcome?: string }>
  | WsEnvelope<'chain', ChainStatus>
  | WsEnvelope<'system', SystemStatusData>;

export interface SystemSnapshot {
  counts: {
    total: number;
    allow: number;
    block: number;
    ask: number;
    attacks_blocked: number;
    tasks_completed: number;
  };
  recent_logs: AuditEntry[];
  messages: AgentMessage[];
  resources: ResourceUsage;
  chain: ChainStatus;
  system: SystemStatusData;
  scenarios: ScenarioItem[];
  pending_asks: AskRequest[];
  network: NetworkEvent[];
}
