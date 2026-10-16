import React from 'react';
import { Bot, Shield, Box, Network, Globe, Database } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';

export const PipelineFlow: React.FC = () => {
  const auditLogs = useLiveStore((s) => s.auditLogs);
  const workspace = useLiveStore((s) => s.workspace);
  const latestLog = auditLogs[0];

  const decision = latestLog ? latestLog.decision : 'allow';
  const isBlock = decision === 'block';
  const isAsk = decision === 'ask';
  const isAllow = decision === 'allow';

  return (
    <div className="flex flex-col h-full rounded-card border border-line bg-surface p-4 justify-between card-hover">
      <div className="flex items-center justify-between pb-2 border-b border-line mb-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-accent" />
          Execution Boundary Pipeline
        </h3>
        {latestLog ? (
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-raised border border-line/60 text-muted">
            Last: <strong className="uppercase text-ink">{latestLog.tool}</strong> (
            <span className={isBlock ? 'text-block font-bold' : isAsk ? 'text-ask font-bold' : 'text-allow font-bold'}>
              {latestLog.decision}
            </span>)
          </span>
        ) : (
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-raised border border-line/60 text-muted">Idle</span>
        )}
      </div>

      {/* Main flow line */}
      <div className="relative py-3 flex items-center justify-between gap-1 text-center select-none w-full">
        {/* Node 1: Agent */}
        <div className="flex-1 min-w-0 max-w-[72px] flex flex-col items-center gap-1 z-10">
          <div className="relative">
            <span className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 rounded-full bg-surface border border-line text-[9px] font-mono font-bold text-muted flex items-center justify-center z-20">1</span>
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg border border-line bg-raised flex items-center justify-center text-accent shadow-sm">
              <Bot className="w-4 h-4" />
            </div>
          </div>
          <span className="text-[10px] sm:text-[11px] font-medium text-ink truncate w-full">Agent</span>
          <span className="text-[9px] text-muted truncate w-full">Untrusted</span>
        </div>

        {/* Connector 1 */}
        <div className="flex-1 min-w-[6px] h-0.5 bg-line relative flex items-center justify-center">
          <div className="absolute inset-0 bg-accent/50 animate-pulse" />
        </div>

        {/* Node 2: Policy Gate */}
        <div className="flex-1 min-w-0 max-w-[72px] flex flex-col items-center gap-1 z-10">
          <div className="relative">
            <span className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 rounded-full bg-surface border border-line text-[9px] font-mono font-bold text-muted flex items-center justify-center z-20">2</span>
            <div
              className={`w-8 h-8 sm:w-9 sm:h-9 rounded-lg border flex items-center justify-center shadow-sm transition-colors duration-300 ${
                isBlock
                  ? 'border-block bg-block-bg text-block ring-2 ring-block/40 animate-pulse-subtle'
                  : isAsk
                  ? 'border-ask bg-ask-bg text-ask ring-2 ring-ask/40 animate-pulse-subtle'
                  : 'border-line bg-raised text-accent'
              }`}
            >
              <Shield className="w-4 h-4" />
            </div>
          </div>
          <span className="text-[10px] sm:text-[11px] font-semibold text-ink truncate w-full">Policy Gate</span>
          <span className={`text-[9px] font-mono truncate w-full ${isBlock ? 'text-block font-bold' : isAsk ? 'text-ask font-bold' : 'text-muted'}`}>
            {isBlock ? '✕ BLOCK' : isAsk ? '? ASK' : 'OPA + ML'}
          </span>
        </div>

        {/* Connector 2 */}
        <div className="flex-1 min-w-[6px] h-0.5 bg-line relative flex items-center justify-center">
          {isAllow && <div className="absolute inset-0 bg-allow/60 animate-pulse" />}
          {isBlock && <div className="absolute inset-0 bg-block/30" />}
        </div>

        {/* Node 3: Isolated Sandbox */}
        <div className="flex-1 min-w-0 max-w-[72px] flex flex-col items-center gap-1 z-10">
          <div className="relative">
            <span className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 rounded-full bg-surface border border-line text-[9px] font-mono font-bold text-muted flex items-center justify-center z-20">3</span>
            <div
              className={`w-8 h-8 sm:w-9 sm:h-9 rounded-lg border flex items-center justify-center shadow-sm transition-colors duration-300 ${
                isAllow ? 'border-allow/50 bg-allow-bg/40 text-allow ring-1 ring-allow/30' : 'border-line bg-raised/50 text-muted opacity-60'
              }`}
            >
              <Box className="w-4 h-4" />
            </div>
          </div>
          <span className="text-[10px] sm:text-[11px] font-medium text-ink truncate w-full">Sandbox</span>
          <span className="text-[9px] text-muted truncate w-full" title={workspace?.name || '/workspace'}>
            {workspace?.name || 'Isolated'}
          </span>
        </div>

        {/* Connector 3 */}
        <div className="flex-1 min-w-[6px] h-0.5 bg-line relative flex items-center justify-center">
          {isAllow && <div className="absolute inset-0 bg-allow/60 animate-pulse" />}
        </div>

        {/* Node 4: Squid Proxy */}
        <div className="flex-1 min-w-0 max-w-[72px] flex flex-col items-center gap-1 z-10">
          <div className="relative">
            <span className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 rounded-full bg-surface border border-line text-[9px] font-mono font-bold text-muted flex items-center justify-center z-20">4</span>
            <div
              className={`w-8 h-8 sm:w-9 sm:h-9 rounded-lg border flex items-center justify-center shadow-sm transition-colors duration-300 ${
                isAllow && latestLog?.tool === 'http'
                  ? 'border-allow/50 bg-allow-bg/40 text-allow ring-1 ring-allow/30'
                  : 'border-line bg-raised/50 text-muted opacity-60'
              }`}
            >
              <Network className="w-4 h-4" />
            </div>
          </div>
          <span className="text-[10px] sm:text-[11px] font-medium text-ink truncate w-full">Proxy</span>
          <span className="text-[9px] text-muted truncate w-full">Allowlist</span>
        </div>

        {/* Connector 4 */}
        <div className="flex-1 min-w-[6px] h-0.5 bg-line relative flex items-center justify-center">
          {isAllow && latestLog?.tool === 'http' && <div className="absolute inset-0 bg-allow/60 animate-pulse" />}
        </div>

        {/* Node 5: Internet */}
        <div className="flex-1 min-w-0 max-w-[72px] flex flex-col items-center gap-1 z-10">
          <div className="relative">
            <span className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 rounded-full bg-surface border border-line text-[9px] font-mono font-bold text-muted flex items-center justify-center z-20">5</span>
            <div
              className={`w-8 h-8 sm:w-9 sm:h-9 rounded-lg border flex items-center justify-center shadow-sm transition-colors duration-300 ${
                isAllow && latestLog?.tool === 'http'
                  ? 'border-allow bg-allow-bg text-allow ring-1 ring-allow/30'
                  : 'border-line bg-raised/50 text-muted opacity-50'
              }`}
            >
              <Globe className="w-4 h-4" />
            </div>
          </div>
          <span className="text-[10px] sm:text-[11px] font-medium text-ink truncate w-full">External</span>
          <span className="text-[9px] text-muted truncate w-full">Target</span>
        </div>
      </div>

      {/* Auxiliary ledger branches */}
      <div className="mt-2 pt-2 border-t border-line flex flex-wrap items-center justify-between gap-1 text-xs text-muted">
        <div className="flex items-center gap-1 font-mono text-[10px] truncate">
          <Shield className="w-3 h-3 text-accent shrink-0" />
          <span className="truncate">ML Prompt Guard: Active</span>
        </div>
        <div className="flex items-center gap-1 font-mono text-[10px] truncate">
          <Database className="w-3 h-3 text-accent shrink-0" />
          <span className="truncate">SHA-256 HMAC Ledger</span>
        </div>
      </div>
    </div>
  );
};
