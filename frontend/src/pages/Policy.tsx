import React from 'react';
import { ShieldCheck, Globe } from 'lucide-react';
import { HashChip } from '@/components/HashChip';
import { DecisionBadge } from '@/components/DecisionBadge';
import { Decision } from '@/api/types';

const RULES = [
  {
    id: 'ESC-001',
    name: 'Host Path Traversal & Rootfs Escape',
    action: 'BLOCK',
    risk: 0.90,
    desc: 'Blocks any file or shell command referencing /etc, /root, /sys, /proc, /dev, or parent traversals outside /workspace.',
  },
  {
    id: 'NET-002',
    name: 'Disallowed Network Egress & Raw Sockets',
    action: 'BLOCK',
    risk: 0.85,
    desc: 'Blocks raw sockets, nmap, netcat, and outbound connections to non-allowlisted domains.',
  },
  {
    id: 'RES-003',
    name: 'Resource Exhaustion & Fork Bombs',
    action: 'BLOCK',
    risk: 0.95,
    desc: 'Detects and denies unbounded recursive loops, process spawning bombs, and memory starvation payloads.',
  },
  {
    id: 'SEC-004',
    name: 'Privilege Escalation & Sudo Attempts',
    action: 'BLOCK',
    risk: 0.90,
    desc: 'Blocks sudo, su, setuid binaries, and attempts to modify system group permissions.',
  },
  {
    id: 'HITL-005',
    name: 'Ambiguous or Modifying Sensitive Files',
    action: 'ASK',
    risk: 0.65,
    desc: 'Triggers interactive Human-in-the-Loop approval before writing to config files or sending external webhooks.',
  },
  {
    id: 'FILE-006',
    name: 'Standard Workspace Read/Write',
    action: 'ALLOW',
    risk: 0.10,
    desc: 'Permits normal reading and writing within /workspace directory for authorized project files.',
  },
];

const ALLOWLIST_DOMAINS = [
  'api.openai.com',
  'api.anthropic.com',
  'huggingface.co',
  'pypi.org',
  'files.pythonhosted.org',
  'registry.npmjs.org',
  'github.com',
  'raw.githubusercontent.com',
];

export const Policy: React.FC = () => {
  return (
    <div className="space-y-4 max-w-[1920px] mx-auto pb-10">
      <div className="flex items-center justify-between pb-3 border-b border-line">
        <div>
          <h2 className="text-base font-bold text-ink">Host Gateway Policy Configuration</h2>
          <p className="text-xs text-muted">
            Declarative security rules evaluated on the host before any command touches the sandbox container.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted font-mono">Policy Hash:</span>
          <HashChip hash="3d9fa82be05e3f4219a1843b0c3f568a912bb098" truncateLength={8} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Policy Rules Table (col 8) */}
        <div className="lg:col-span-8 rounded-card border border-line bg-surface p-4 space-y-3 card-hover">
          <div className="flex items-center gap-2 pb-2 border-b border-line">
            <ShieldCheck className="w-4 h-4 text-accent" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
              Active Security Rules
            </h3>
          </div>

          <div className="space-y-2.5">
            {RULES.map((rule) => {
              return (
                <div
                  key={rule.id}
                  className="p-3 rounded-xl border border-line/70 bg-raised/30 hover:bg-raised/60 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-accent px-1.5 py-0.5 rounded bg-raised border border-line/60">
                        {rule.id}
                      </span>
                      <span className="font-semibold text-xs text-ink">{rule.name}</span>
                    </div>
                    <p className="text-[11px] text-muted leading-relaxed max-w-xl">
                      {rule.desc}
                    </p>
                  </div>

                  <div className="flex items-center gap-2.5 shrink-0">
                    <span className="text-[10px] font-mono text-muted bg-raised px-1.5 py-0.5 rounded border border-line/40">
                      Risk &gt; {rule.risk}
                    </span>
                    <DecisionBadge decision={rule.action.toLowerCase() as Decision} size="sm" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Egress Allowlist & Capabilities (col 4) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="rounded-card border border-line bg-surface p-4 space-y-3 card-hover">
            <div className="flex items-center gap-2 pb-2 border-b border-line">
              <Globe className="w-4 h-4 text-accent" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
                Squid Proxy Egress Allowlist
              </h3>
            </div>

            <p className="text-[11px] text-muted leading-relaxed">
              Strict DNS + HTTP domain matching. Any external connection outside this list is immediately dropped with HTTP 403 Forbidden.
            </p>

            <div className="space-y-1 font-mono text-xs max-h-60 overflow-y-auto">
              {ALLOWLIST_DOMAINS.map((domain, i) => (
                <div key={i} className="p-1.5 px-2.5 rounded bg-raised/60 border border-line text-ink flex items-center justify-between">
                  <span>{domain}</span>
                  <span className="text-[10px] text-allow font-bold">ALLOWED</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-card border border-line bg-surface p-4 space-y-2 text-xs">
            <span className="text-muted block text-[11px] uppercase tracking-wider font-semibold">
              Policy Architecture Notice
            </span>
            <p className="text-muted text-[11px] leading-relaxed">
              Rules are evaluated deterministically in Python/OPA on the host before docker container dispatch. Prompt Guard 2 acts as a confidence signal that can only escalate strictness—never relax a rule.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
