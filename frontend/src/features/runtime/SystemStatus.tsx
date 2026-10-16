import React from 'react';
import { Activity, CheckCircle2, AlertCircle } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';

export const SystemStatus: React.FC = () => {
  const system = useLiveStore((s) => s.system);

  const formatUptime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h}h ${m}m ${s}s`;
  };

  return (
    <div className="rounded-card border border-line bg-surface p-4 flex flex-col justify-between h-full">
      <div className="flex items-center justify-between pb-2 border-b border-line mb-3">
        <div className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-accent" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
            Platform Subsystem Health
          </h3>
        </div>
        <span className="text-[11px] font-mono text-muted">
          Up: {formatUptime(system.uptime_s)}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        {Object.entries(system.components).map(([name, status]) => {
          const isHealthy = ['running', 'active', 'logging', 'connected'].includes(status);
          return (
            <div
              key={name}
              className="p-2 rounded-lg border border-line/60 bg-raised/30 flex items-center justify-between"
            >
              <span className="text-ink text-[11px] font-medium truncate mr-1">{name}</span>
              <span className="flex items-center gap-1 shrink-0 font-mono text-[10px] capitalize">
                {isHealthy ? (
                  <>
                    <CheckCircle2 className="w-3 h-3 text-allow" />
                    <span className="text-allow">{status}</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-3 h-3 text-block" />
                    <span className="text-block">{status}</span>
                  </>
                )}
              </span>
            </div>
          );
        })}
      </div>

      <div className="mt-3 pt-2 border-t border-line flex items-center justify-between text-[11px] font-mono text-muted">
        <span>Security Mode:</span>
        <span className={`font-bold uppercase ${system.sandbox === 'on' ? 'text-allow' : 'text-block'}`}>
          {system.sandbox === 'on' ? 'HARDENED ENFORCEMENT' : 'UNSAFE (SANDBOX OFF)'}
        </span>
      </div>
    </div>
  );
};
