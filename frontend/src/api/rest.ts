import { SystemSnapshot, AuditEntry, ScenarioItem, ChainStatus, WorkspaceInfo, WorkspaceBrowseResult } from './types';

const BASE_URL = '';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API error ${res.status}: ${errorText}`);
  }

  return res.json();
}

export const api = {
  getSnapshot: async (sinceSeq?: number): Promise<SystemSnapshot> => {
    const query = sinceSeq ? `?since=${sinceSeq}` : '';
    return fetchJson<SystemSnapshot>(`/api/snapshot${query}`);
  },

  getAuditLogs: async (params?: {
    cursor?: number;
    limit?: number;
    decision?: string;
    tool?: string;
    q?: string;
  }): Promise<{ entries: AuditEntry[]; total: number; next_cursor?: number }> => {
    const searchParams = new URLSearchParams();
    if (params?.cursor) searchParams.set('cursor', String(params.cursor));
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.decision && params.decision !== 'all') searchParams.set('decision', params.decision);
    if (params?.tool && params.tool !== 'all') searchParams.set('tool', params.tool);
    if (params?.q) searchParams.set('q', params.q);

    return fetchJson(`/api/audit?${searchParams.toString()}`);
  },

  verifyChain: async (): Promise<ChainStatus> => {
    return fetchJson<ChainStatus>('/api/audit/verify', { method: 'POST' });
  },

  tamperTest: async (): Promise<{ ok: boolean; message: string }> => {
    return fetchJson('/api/audit/tamper', { method: 'POST' });
  },

  clearAuditLogs: async (): Promise<{ ok: boolean; message: string }> => {
    return fetchJson('/api/audit/clear', { method: 'POST' });
  },

  getScenarios: async (): Promise<ScenarioItem[]> => {
    return fetchJson<ScenarioItem[]>('/api/scenarios');
  },

  runScenario: async (id: string): Promise<{ ok: boolean; task_id?: string }> => {
    return fetchJson(`/api/scenarios/${encodeURIComponent(id)}/run`, { method: 'POST' });
  },

  runAllScenarios: async (kind: 'attack' | 'normal'): Promise<{ ok: boolean }> => {
    return fetchJson(`/api/scenarios/run-all?kind=${kind}`, { method: 'POST' });
  },

  setSandboxMode: async (mode: 'on' | 'off', confirm: boolean = true): Promise<{ ok: boolean; mode: 'on' | 'off' }> => {
    return fetchJson('/api/sandbox', {
      method: 'POST',
      body: JSON.stringify({ mode, confirm }),
    });
  },

  resolveAsk: async (auditId: number, outcome: 'approve' | 'deny'): Promise<{ ok: boolean }> => {
    return fetchJson(`/api/ask/${auditId}`, {
      method: 'POST',
      body: JSON.stringify({ outcome }),
    });
  },

  getPolicy: async (): Promise<{
    version: string;
    policy_hash: string;
    rules: Array<{ id: string; name: string; description: string; action: string; level: string }>;
    egress_domains: string[];
    allowed_tools: string[];
  }> => {
    return fetchJson('/api/policy');
  },

  chatAgent: async (prompt: string, taskId?: string): Promise<{
    ok: boolean;
    model: string;
    thought?: string;
    content?: string;
    tool_calls?: Array<{ id: string; name: string; args: any }>;
    decisions?: Array<{
      tool: string;
      args: any;
      decision: string;
      reason: string;
      rule_id: string;
      score: number;
      result?: any;
      audit_id: number;
    }>;
    error?: string;
  }> => {
    return fetchJson('/api/agent/chat', {
      method: 'POST',
      body: JSON.stringify({ prompt, task_id: taskId || 'live-demo' }),
    });
  },

  getWorkspace: async (): Promise<WorkspaceInfo> => {
    return fetchJson<WorkspaceInfo>('/api/workspace');
  },

  setWorkspace: async (path: string): Promise<{ ok: boolean; workspace: WorkspaceInfo }> => {
    return fetchJson<{ ok: boolean; workspace: WorkspaceInfo }>('/api/workspace', {
      method: 'POST',
      body: JSON.stringify({ path }),
    });
  },

  browseWorkspace: async (dirPath?: string): Promise<WorkspaceBrowseResult> => {
    const query = dirPath ? `?dir_path=${encodeURIComponent(dirPath)}` : '';
    return fetchJson<WorkspaceBrowseResult>(`/api/workspace/browse${query}`);
  },
};

