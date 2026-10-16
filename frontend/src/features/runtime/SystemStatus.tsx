import React from 'react';
import { CheckCircle2, AlertCircle } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';

export const SystemStatus: React.FC = () => {
  const system = useLiveStore((s) => s.system);

  const formatUptime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h}h ${m}m ${s}s`;
  };

  const healthyCount = Object.values(system.components).filter((s) =>
    ['running', 'active', 'logging', 'connected'].includes(s)
  ).length;
  const totalCount = Object.keys(system.components).length || 6;

  return (
    <div className="rounded-card border border-line bg-surface p-3.5 flex flex-col justify-between h-full overflow-hidden card-hover">
      <div>
        <div className="flex items-center justify-between pb-2 border-b border-line mb-2.5">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-allow animate-pulse" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
              Platform Subsystems
            </h3>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-mono text-allow bg-allow-bg/60 px-1.5 py-0.5 rounded border border-allow/30 font-bold">
              {healthyCount}/{totalCount} OK
            </span>
            <span className="text-[10px] font-mono text-muted bg-raised/60 px-1.5 py-0.5 rounded border border-line/40">
              {formatUptime(system.uptime_s)}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-1.5 text-xs">
          {Object.entries(system.components).map(([name, status]) => {
            const isHealthy = ['running', 'active', 'logging', 'connected'].includes(status);
            const shortName = name
              .replace('Host ', '')
              .replace(' Engine', '')
              .replace(' Proxy', '')
              .replace(' DNS', '')
              .replace('Audit ', '')
              .replace('Docker ', '');

            return (
              <div
                key={name}
                title={`${name}: ${status}`}
                className="px-2 py-1.5 rounded-lg border border-line/60 bg-raised/30 flex items-center justify-between gap-1 min-w-0"
              >
                <span className="text-ink text-[11px] font-medium truncate">{shortName}</span>
                <span className="flex items-center gap-1 shrink-0 font-mono text-[10px] capitalize">
                  {isHealthy ? (
                    <>
                      <CheckCircle2 className="w-2.5 h-2.5 text-allow" />
                      <span className="text-allow">{status}</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-2.5 h-2.5 text-block" />
                      <span className="text-block">{status}</span>
                    </>
                  )}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-2.5 pt-2 border-t border-line flex items-center justify-between text-[10px] font-mono text-muted">
        <span>Security Mode:</span>
        <span className={`font-bold uppercase ${system.sandbox === 'on' ? 'text-allow' : 'text-block'}`}>
          {system.sandbox === 'on' ? 'HARDENED' : 'UNSAFE (OFF)'}
        </span>
      </div>
    </div>
  );
};
