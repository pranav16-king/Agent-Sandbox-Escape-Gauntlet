import React from 'react';
import { Network, Globe } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';
import { DecisionBadge } from '@/components/DecisionBadge';

export const NetworkTable: React.FC<{ maxHeight?: string }> = ({ maxHeight = 'max-h-[220px]' }) => {
  const networkEvents = useLiveStore((s) => s.networkEvents);

  return (
    <div className="rounded-card border border-line bg-surface p-4 flex flex-col justify-between h-full">
      <div className="flex items-center justify-between pb-2 border-b border-line mb-2">
        <div className="flex items-center gap-1.5">
          <Network className="w-3.5 h-3.5 text-accent" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
            Egress Network & DNS Monitor
          </h3>
        </div>
        <span className="text-[11px] font-mono text-muted">
          Squid + dnsmasq
        </span>
      </div>

      <div className={`overflow-y-auto space-y-1.5 ${maxHeight}`}>
        {networkEvents.length === 0 ? (
          <div className="h-28 flex flex-col items-center justify-center text-muted text-xs">
            <Globe className="w-6 h-6 mb-1 opacity-40" />
            <span>No egress traffic observed.</span>
          </div>
        ) : (
          networkEvents.map((evt, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2 rounded-lg border border-line/60 bg-raised/30 text-xs font-mono"
            >
              <div className="flex items-center gap-2 truncate">
                <span className="text-[10px] px-1 py-0.5 rounded bg-raised text-muted font-bold">
                  {evt.type}
                </span>
                <span className="text-ink truncate font-medium max-w-[160px]" title={evt.target}>
                  {evt.target}
                </span>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <span className="text-[10px] text-accent font-semibold">{evt.rule_id}</span>
                <DecisionBadge decision={evt.action} size="sm" />
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-2 pt-2 border-t border-line text-[10px] font-mono text-muted flex items-center justify-between">
        <span>Default Policy: DROP_ALL</span>
        <span>Allowlist: api.openai.com, huggingface.co</span>
      </div>
    </div>
  );
};
