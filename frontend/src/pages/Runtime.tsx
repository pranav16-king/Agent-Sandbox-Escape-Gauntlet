import React from 'react';
import { Lock } from 'lucide-react';
import { ResourceGauges } from '@/features/runtime/ResourceGauges';
import { NetworkTable } from '@/features/runtime/NetworkTable';
import { SystemStatus } from '@/features/runtime/SystemStatus';

export const Runtime: React.FC = () => {
  return (
    <div className="space-y-4 max-w-[1920px] mx-auto pb-10">
      <div className="flex items-center justify-between pb-3 border-b border-line">
        <div>
          <h2 className="text-base font-bold text-ink">Runtime & Network Isolation</h2>
          <p className="text-xs text-muted">
            Kernel isolation, cgroup resource limits, seccomp filters, and Squid egress boundary status.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Gauges & Status (col 5) */}
        <div className="lg:col-span-5 space-y-4">
          <ResourceGauges />
          <SystemStatus />
        </div>

        {/* Right: Network Table & Hardening Parameters (col 7) */}
        <div className="lg:col-span-7 space-y-4">
          <NetworkTable maxHeight="max-h-[300px]" />

          {/* Hardened Container Specification Card */}
          <div className="rounded-card border border-line bg-surface p-4 space-y-3 card-hover">
            <div className="flex items-center gap-2 pb-2 border-b border-line">
              <Lock className="w-4 h-4 text-accent" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
                Runtime Sandboxing Flags
              </h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3 rounded-lg border border-line bg-raised/40 space-y-1 hover:border-line/80 transition-colors">
                <span className="text-muted block text-[10px]">FILESYSTEM ISOLATION</span>
                <span className="font-bold text-ink bg-surface px-1.5 py-0.5 rounded border border-line/60 inline-block">--read-only</span>
                <p className="text-[11px] text-muted font-sans">
                  Root container rootfs is read-only. Only <code>/workspace</code> allows writes.
                </p>
              </div>

              <div className="p-3 rounded-lg border border-line bg-raised/40 space-y-1">
                <span className="text-muted block text-[10px]">LINUX CAPABILITIES</span>
                <span className="font-bold text-ink">--cap-drop=ALL</span>
                <p className="text-[11px] text-muted font-sans">
                  All kernel capabilities stripped, including CAP_SYS_ADMIN, CAP_NET_RAW.
                </p>
              </div>

              <div className="p-3 rounded-lg border border-line bg-raised/40 space-y-1">
                <span className="text-muted block text-[10px]">PROCESS PRIVILEGE</span>
                <span className="font-bold text-ink">--user 1000:1000</span>
                <p className="text-[11px] text-muted font-sans">
                  Non-root unprivileged process execution with no privilege escalation.
                </p>
              </div>

              <div className="p-3 rounded-lg border border-line bg-raised/40 space-y-1">
                <span className="text-muted block text-[10px]">EGRESS PROXY</span>
                <span className="font-bold text-ink">http_proxy=squid:3128</span>
                <p className="text-[11px] text-muted font-sans">
                  Only HTTP/HTTPS through allowlisted domains. Direct raw socket traffic dropped.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
