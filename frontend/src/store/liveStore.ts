import { create } from 'zustand';
import {
  AuditEntry,
  AgentMessage,
  AskRequest,
  NetworkEvent,
  ResourceUsage,
  ScenarioItem,
  ChainStatus,
  SystemStatusData,
  SystemSnapshot,
  LiveEvent,
  WorkspaceInfo,
} from '@/api/types';

const MAX_AUDIT_LOGS = 2000;
const MAX_TIMELINE_POINTS = 300;
const MAX_MESSAGES = 100;
const MAX_NETWORK_EVENTS = 100;

export interface TimelineDataPoint {
  time: string;
  allowed: number;
  blocked: number;
  ask: number;
}

export interface LiveState {
  counts: {
    total: number;
    allow: number;
    block: number;
    ask: number;
    attacks_blocked: number;
    tasks_completed: number;
  };
  auditLogs: AuditEntry[];
  timelinePoints: TimelineDataPoint[];
  agentMessages: AgentMessage[];
  pendingAsks: AskRequest[];
  networkEvents: NetworkEvent[];
  resources: ResourceUsage;
  chain: ChainStatus;
  system: SystemStatusData;
  scenarios: ScenarioItem[];
  workspace: WorkspaceInfo;
  connectionStatus: 'connected' | 'reconnecting' | 'offline';
  retryCount: number;
  lastSeq: number;
  lastBlockTime: number | null;

  // Actions
  setSnapshot: (snapshot: SystemSnapshot) => void;
  ingestEvent: (event: LiveEvent) => void;
  resolveAsk: (auditId: number, outcome: 'approved' | 'denied' | 'timeout') => void;
  setConnectionStatus: (status: 'connected' | 'reconnecting' | 'offline', retryCount?: number) => void;
  setSandboxMode: (mode: 'on' | 'off') => void;
  updateChainStatus: (chain: ChainStatus) => void;
  updateScenarioStatus: (id: string, status: ScenarioItem['status'], outcome?: string) => void;
  setWorkspaceInfo: (workspace: WorkspaceInfo) => void;
  mergeAuditLogs: (entries: AuditEntry[]) => void;
  clearLogs: () => void;
}

export const useLiveStore = create<LiveState>((set) => ({
  counts: {
    total: 0,
    allow: 0,
    block: 0,
    ask: 0,
    attacks_blocked: 0,
    tasks_completed: 0,
  },
  auditLogs: [],
  timelinePoints: [],
  agentMessages: [],
  pendingAsks: [],
  networkEvents: [],
  resources: {
    cpu_pct: 0,
    mem_mb: 0,
    mem_limit_mb: 0,
    disk_mb: 0,
    disk_limit_mb: 0,
    pids: 0,
    pids_limit: 0,
  },
  chain: {
    ok: true,
    entries: 0,
    head_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    last_verified: new Date().toISOString(),
  },
  system: {
    sandbox: 'on',
    components: {
      'Host Gateway': 'running',
      'Policy Engine': 'active',
      'Squid Proxy': 'logging',
      'dnsmasq DNS': 'active',
      'Audit Ledger': 'connected',
      'Docker Sandbox': 'running',
    },
    uptime_s: 0,
  },
  scenarios: [],
  workspace: {
    path: '/workspace',
    name: 'workspace',
    is_valid: true,
    file_count: 0,
    files: [],
    allowed_boundary: '/workspace',
  },
  connectionStatus: 'offline',
  retryCount: 0,
  lastSeq: 0,
  lastBlockTime: null,

  setSnapshot: (snapshot) => {
    // Generate initial timeline aggregation from recent logs
    const timeline = generateInitialTimeline(snapshot.recent_logs);

    set({
      counts: snapshot.counts,
      auditLogs: snapshot.recent_logs.slice(0, MAX_AUDIT_LOGS),
      timelinePoints: timeline,
      agentMessages: snapshot.messages || [],
      pendingAsks: snapshot.pending_asks || [],
      networkEvents: snapshot.network || [],
      resources: snapshot.resources,
      chain: snapshot.chain,
      system: snapshot.system,
      scenarios: snapshot.scenarios,
      ...(snapshot.workspace ? { workspace: snapshot.workspace } : {}),
    });
  },

  ingestEvent: (event) => {
    set((state) => {
      const nextSeq = Math.max(state.lastSeq, event.seq || 0);

      switch (event.type) {
        case 'audit': {
          const entry = event.data as AuditEntry;
          if (!entry || entry.id === undefined || entry.id === null) {
            return { lastSeq: nextSeq };
          }

          // Deduplicate by entry.id: if already present, do not duplicate
          const alreadyExists = state.auditLogs.some((l) => l.id === entry.id);
          if (alreadyExists) {
            return { lastSeq: nextSeq };
          }

          // Insert / prepend in descending ID order
          const newLogs = [entry, ...state.auditLogs]
            .sort((a, b) => (b.id !== a.id ? b.id - a.id : new Date(b.ts).getTime() - new Date(a.ts).getTime()))
            .slice(0, MAX_AUDIT_LOGS);

          const isBlock = entry.decision === 'block';
          const isAllow = entry.decision === 'allow';
          const isAsk = entry.decision === 'ask';

          const nextCounts = {
            ...state.counts,
            total: Math.max(state.counts.total + 1, newLogs.length),
            allow: state.counts.allow + (isAllow ? 1 : 0),
            block: state.counts.block + (isBlock ? 1 : 0),
            ask: state.counts.ask + (isAsk ? 1 : 0),
            attacks_blocked: state.counts.attacks_blocked + (isBlock ? 1 : 0),
          };

          // Update timeline
          const timeLabel = new Date(entry.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          let nextTimeline = [...state.timelinePoints];
          const lastPoint = nextTimeline[nextTimeline.length - 1];

          if (lastPoint && lastPoint.time === timeLabel) {
            lastPoint.allowed += isAllow ? 1 : 0;
            lastPoint.blocked += isBlock ? 1 : 0;
            lastPoint.ask += isAsk ? 1 : 0;
          } else {
            nextTimeline.push({
              time: timeLabel,
              allowed: isAllow ? 1 : 0,
              blocked: isBlock ? 1 : 0,
              ask: isAsk ? 1 : 0,
            });
            if (nextTimeline.length > MAX_TIMELINE_POINTS) {
              nextTimeline = nextTimeline.slice(nextTimeline.length - MAX_TIMELINE_POINTS);
            }
          }

          // If entry was generated by a tool call, inject into agent feed
          const autoMessage: AgentMessage | null = entry.agent_thought
            ? {
                id: `thought-${entry.id}`,
                role: 'agent',
                text: `${entry.agent_thought}\n[Call ${entry.tool} ${entry.args}]`,
                ts: entry.ts,
              }
            : null;

          const updatedMessages = autoMessage
            ? [...state.agentMessages, autoMessage].slice(-MAX_MESSAGES)
            : state.agentMessages;

          return {
            lastSeq: nextSeq,
            counts: nextCounts,
            auditLogs: newLogs,
            timelinePoints: nextTimeline,
            agentMessages: updatedMessages,
            lastBlockTime: isBlock ? Date.now() : state.lastBlockTime,
          };
        }

        case 'agent_message': {
          const msg = event.data as AgentMessage;
          const messages = state.agentMessages;

          // 1. Exact match by message ID
          const existingByIdx = msg.id ? messages.findIndex((m) => m.id === msg.id) : -1;
          if (existingByIdx !== -1) {
            const updated = [...messages];
            updated[existingByIdx] = { ...updated[existingByIdx], ...msg };
            return {
              lastSeq: nextSeq,
              agentMessages: updated,
            };
          }

          // 2. Deduplicate user message if optimistically ingested recently
          if (msg.role === 'user') {
            const searchSlice = messages.slice(-6);
            const optimisticOffset = searchSlice.findIndex(
              (m) => m.role === 'user' && m.text.trim() === msg.text.trim()
            );
            if (optimisticOffset !== -1) {
              const realIdx = messages.length - searchSlice.length + optimisticOffset;
              const updated = [...messages];
              updated[realIdx] = { ...updated[realIdx], ...msg };
              return {
                lastSeq: nextSeq,
                agentMessages: updated,
              };
            }
          }

          return {
            lastSeq: nextSeq,
            agentMessages: [...messages, msg].slice(-MAX_MESSAGES),
          };
        }

        case 'ask_request': {
          const ask = event.data as AskRequest;
          const exists = state.pendingAsks.some((a) => a.audit_id === ask.audit_id);
          return {
            lastSeq: nextSeq,
            pendingAsks: exists ? state.pendingAsks : [ask, ...state.pendingAsks],
          };
        }

        case 'ask_resolved': {
          const resolved = event.data as { audit_id: number; outcome: 'approved' | 'denied' | 'timeout' };
          return {
            lastSeq: nextSeq,
            pendingAsks: state.pendingAsks.filter((a) => a.audit_id !== resolved.audit_id),
          };
        }

        case 'network': {
          const net = event.data as NetworkEvent;
          return {
            lastSeq: nextSeq,
            networkEvents: [{ ...net, ts: net.ts || new Date().toISOString() }, ...state.networkEvents].slice(0, MAX_NETWORK_EVENTS),
          };
        }

        case 'resources': {
          return {
            lastSeq: nextSeq,
            resources: event.data as ResourceUsage,
          };
        }

        case 'chain': {
          return {
            lastSeq: nextSeq,
            chain: event.data as ChainStatus,
          };
        }

        case 'scenario': {
          const scen = event.data as { id: string; status: ScenarioItem['status']; outcome?: string };
          const updated = state.scenarios.map((s) =>
            s.id === scen.id ? { ...s, status: scen.status, outcome: scen.outcome ?? s.outcome } : s
          );
          return {
            lastSeq: nextSeq,
            scenarios: updated,
          };
        }

        case 'system': {
          return {
            lastSeq: nextSeq,
            system: event.data as SystemStatusData,
          };
        }

        case 'clear_logs': {
          return {
            lastSeq: nextSeq,
            counts: {
              total: 0,
              allow: 0,
              block: 0,
              ask: 0,
              attacks_blocked: 0,
              tasks_completed: 0,
            },
            auditLogs: [],
            timelinePoints: [],
            agentMessages: [],
            pendingAsks: [],
            chain: {
              ok: true,
              entries: 0,
              head_hash: '0'.repeat(64),
              last_verified: new Date().toISOString(),
            },
          };
        }

        case 'workspace': {
          return {
            lastSeq: nextSeq,
            workspace: event.data as WorkspaceInfo,
          };
        }

        default:
          return { lastSeq: nextSeq };
      }
    });
  },

  resolveAsk: (auditId, outcome) => {
    set((state) => ({
      pendingAsks: state.pendingAsks.filter((a) => a.audit_id !== auditId),
      counts: {
        ...state.counts,
        allow: outcome === 'approved' ? state.counts.allow + 1 : state.counts.allow,
        block: outcome !== 'approved' ? state.counts.block + 1 : state.counts.block,
      },
    }));
  },

  mergeAuditLogs: (entries: AuditEntry[]) => {
    if (!entries || entries.length === 0) return;
    set((state) => {
      const existingMap = new Map<number, AuditEntry>();
      for (const log of state.auditLogs) {
        existingMap.set(log.id, log);
      }
      for (const log of entries) {
        if (log && log.id !== undefined && log.id !== null) {
          existingMap.set(log.id, log);
        }
      }
      const mergedLogs = Array.from(existingMap.values())
        .sort((a, b) => (b.id !== a.id ? b.id - a.id : new Date(b.ts).getTime() - new Date(a.ts).getTime()))
        .slice(0, MAX_AUDIT_LOGS);

      const countAllow = mergedLogs.filter((e) => e.decision === 'allow').length;
      const countBlock = mergedLogs.filter((e) => e.decision === 'block').length;
      const countAsk = mergedLogs.filter((e) => e.decision === 'ask').length;
      const totalCount = Math.max(state.counts.total, mergedLogs.length);

      return {
        auditLogs: mergedLogs,
        counts: {
          ...state.counts,
          total: totalCount,
          allow: Math.max(state.counts.allow, countAllow),
          block: Math.max(state.counts.block, countBlock),
          ask: Math.max(state.counts.ask, countAsk),
          attacks_blocked: Math.max(state.counts.attacks_blocked, countBlock),
        },
      };
    });
  },

  clearLogs: () => {
    set({
      counts: {
        total: 0,
        allow: 0,
        block: 0,
        ask: 0,
        attacks_blocked: 0,
        tasks_completed: 0,
      },
      auditLogs: [],
      timelinePoints: [],
      agentMessages: [],
      pendingAsks: [],
      chain: {
        ok: true,
        entries: 0,
        head_hash: '0'.repeat(64),
        last_verified: new Date().toISOString(),
      },
    });
  },

  setWorkspaceInfo: (workspace) => set({ workspace }),

  setConnectionStatus: (status, retryCount = 0) => set({ connectionStatus: status, retryCount }),
  setSandboxMode: (mode) => set((s) => ({ system: { ...s.system, sandbox: mode } })),
  updateChainStatus: (chain) => set({ chain }),
  updateScenarioStatus: (id, status, outcome) => {
    set((state) => ({
      scenarios: state.scenarios.map((s) => (s.id === id ? { ...s, status, outcome: outcome || s.outcome } : s)),
    }));
  },
}));

function generateInitialTimeline(logs: AuditEntry[]): TimelineDataPoint[] {
  if (!logs || logs.length === 0) {
    return [];
  }

  // Aggregate by time string
  const map = new Map<string, { allowed: number; blocked: number; ask: number }>();
  logs.forEach((log) => {
    const timeLabel = new Date(log.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const current = map.get(timeLabel) || { allowed: 0, blocked: 0, ask: 0 };
    if (log.decision === 'allow') current.allowed++;
    else if (log.decision === 'block') current.blocked++;
    else if (log.decision === 'ask') current.ask++;
    map.set(timeLabel, current);
  });

  return Array.from(map.entries())
    .map(([time, data]) => ({ time, ...data }))
    .slice(-MAX_TIMELINE_POINTS);
}
