import React from 'react';
import { Bot, Shield, Box, Network, Globe, Database, Monitor } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';

export const PipelineFlow: React.FC = () => {
  const auditLogs = useLiveStore((s) => s.auditLogs);
  const latestLog = auditLogs[0];

  const decision = latestLog ? latestLog.decision : 'allow';
  const isBlock = decision === 'block';
  const isAsk = decision === 'ask';
  const isAllow = decision === 'allow';

  return (
    <div className="flex flex-col h-full rounded-card border border-line bg-surface p-4 justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-line mb-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-accent" />
          Execution Boundary Pipeline
        </h3>
        {latestLog ? (
          <span className="text-[11px] font-mono text-muted">
            Last: <strong className="uppercase text-ink">{latestLog.tool}</strong> ({latestLog.decision})
          </span>
        ) : (
          <span className="text-[11px] font-mono text-muted">Idle</span>
        )}
      </div>

      {/* Main flow line */}
      <div className="relative py-4 flex items-center justify-between gap-1 text-center select-none overflow-x-auto">
        {/* Node 1: Agent */}
        <div className="flex flex-col items-center gap-1.5 z-10 min-w-[70px]">
          <div className="w-10 h-10 rounded-xl border border-line bg-raised flex items-center justify-center text-accent shadow-sm">
            <Bot className="w-5 h-5" />
          </div>
          <span className="text-[11px] font-medium text-ink">Agent</span>
          <span className="text-[9px] text-muted">Untrusted</span>
        </div>

        {/* Connector 1 */}
        <div className="flex-1 h-0.5 bg-line relative flex items-center justify-center">
          <div className="absolute inset-0 bg-accent/50 animate-pulse" />
        </div>

        {/* Node 2: Policy Gate */}
        <div className="flex flex-col items-center gap-1.5 z-10 min-w-[80px]">
          <div
            className={`w-10 h-10 rounded-xl border flex items-center justify-center shadow-sm transition-colors duration-300 ${
              isBlock
                ? 'border-block bg-block-bg text-block ring-2 ring-block/40'
                : isAsk
                ? 'border-ask bg-ask-bg text-ask ring-2 ring-ask/40'
                : 'border-line bg-raised text-accent'
            }`}
          >
            <Shield className="w-5 h-5" />
          </div>
          <span className="text-[11px] font-semibold text-ink">Policy Gate</span>
          <span className={`text-[9px] font-mono ${isBlock ? 'text-block font-bold' : isAsk ? 'text-ask font-bold' : 'text-muted'}`}>
            {isBlock ? 'BLOCKED' : isAsk ? 'PENDING' : 'Host Control'}
          </span>
        </div>

        {/* Connector 2 */}
        <div className="flex-1 h-0.5 bg-line relative flex items-center justify-center">
          {isAllow && <div className="absolute inset-0 bg-allow/60 animate-pulse" />}
          {isBlock && <div className="absolute inset-0 bg-block/30" />}
        </div>

        {/* Node 3: Isolated Sandbox */}
        <div className="flex flex-col items-center gap-1.5 z-10 min-w-[80px]">
          <div
            className={`w-10 h-10 rounded-xl border flex items-center justify-center shadow-sm transition-colors duration-300 ${
              isAllow ? 'border-allow/50 bg-allow-bg/40 text-allow' : 'border-line bg-raised/50 text-muted opacity-60'
            }`}
          >
            <Box className="w-5 h-5" />
          </div>
          <span className="text-[11px] font-medium text-ink">Sandbox</span>
          <span className="text-[9px] text-muted">/workspace</span>
        </div>

        {/* Connector 3 */}
        <div className="flex-1 h-0.5 bg-line relative flex items-center justify-center">
          {isAllow && <div className="absolute inset-0 bg-allow/60 animate-pulse" />}
        </div>

        {/* Node 4: Squid Proxy */}
        <div className="flex flex-col items-center gap-1.5 z-10 min-w-[80px]">
          <div
            className={`w-10 h-10 rounded-xl border flex items-center justify-center shadow-sm transition-colors duration-300 ${
              isAllow && latestLog?.tool === 'http'
                ? 'border-allow/50 bg-allow-bg/40 text-allow'
                : 'border-line bg-raised/50 text-muted opacity-60'
            }`}
          >
            <Network className="w-5 h-5" />
          </div>
          <span className="text-[11px] font-medium text-ink">Egress Proxy</span>
          <span className="text-[9px] text-muted">Allowlist</span>
        </div>

        {/* Connector 4 */}
        <div className="flex-1 h-0.5 bg-line relative flex items-center justify-center">
          {isAllow && latestLog?.tool === 'http' && <div className="absolute inset-0 bg-allow/60 animate-pulse" />}
        </div>

        {/* Node 5: Internet */}
        <div className="flex flex-col items-center gap-1.5 z-10 min-w-[70px]">
          <div
            className={`w-10 h-10 rounded-xl border flex items-center justify-center shadow-sm transition-colors duration-300 ${
              isAllow && latestLog?.tool === 'http'
                ? 'border-allow bg-allow-bg text-allow'
                : 'border-line bg-raised/50 text-muted opacity-50'
            }`}
          >
            <Globe className="w-5 h-5" />
          </div>
          <span className="text-[11px] font-medium text-ink">External</span>
          <span className="text-[9px] text-muted">Target Web</span>
        </div>
      </div>

      {/* Auxiliary ledger branches */}
      <div className="mt-2 pt-2 border-t border-line flex items-center justify-around text-xs text-muted">
        <div className="flex items-center gap-1.5 font-mono text-[11px]">
          <Database className="w-3.5 h-3.5 text-accent" />
          <span>SHA-256 Ledger: Tamper-Evident</span>
        </div>
        <div className="flex items-center gap-1.5 font-mono text-[11px]">
          <Monitor className="w-3.5 h-3.5 text-muted" />
          <span>Realtime Telemetry Streamed</span>
        </div>
      </div>
    </div>
  );
};
