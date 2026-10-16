import React from 'react';
import { Cpu, HardDrive, Layers, Server } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';

interface GaugeRowProps {
  label: string;
  current: number;
  limit: number;
  unit: string;
  icon: React.ReactNode;
}

const GaugeRow: React.FC<GaugeRowProps> = ({ label, current, limit, unit, icon }) => {
  const pct = Math.min(100, Math.round((current / limit) * 100));

  let barColor = 'bg-allow';
  let textColor = 'text-ink';
  if (pct >= 90) {
    barColor = 'bg-block';
    textColor = 'text-block font-bold';
  } else if (pct >= 75) {
    barColor = 'bg-ask';
    textColor = 'text-ask font-semibold';
  }

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center gap-1.5 text-muted">
          {icon}
          <span>{label}</span>
        </span>
        <span className={`font-mono text-[11px] ${textColor}`}>
          {current} / {limit} {unit} ({pct}%)
        </span>
      </div>

      <div
        className="w-full h-2 rounded-full bg-raised overflow-hidden border border-line"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-full transition-all duration-300 rounded-full ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

export const ResourceGauges: React.FC = () => {
  const resources = useLiveStore((s) => s.resources);

  return (
    <div className="rounded-card border border-line bg-surface p-4 flex flex-col justify-between h-full card-hover">
      <div className="flex items-center justify-between pb-2 border-b border-line mb-3">
        <div className="flex items-center gap-1.5">
          <Server className="w-3.5 h-3.5 text-accent" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
            Container Cgroup & Limits
          </h3>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-raised text-muted border border-line">
          Enforced
        </span>
      </div>

      <div className="space-y-3.5">
        <GaugeRow
          label="CPU Core Load"
          current={Math.round(resources.cpu_pct)}
          limit={100}
          unit="%"
          icon={<Cpu className="w-3.5 h-3.5 text-muted" />}
        />
        <GaugeRow
          label="RAM Memory"
          current={resources.mem_mb}
          limit={resources.mem_limit_mb}
          unit="MB"
          icon={<Layers className="w-3.5 h-3.5 text-muted" />}
        />
        <GaugeRow
          label="Disk Workspace"
          current={resources.disk_mb}
          limit={resources.disk_limit_mb}
          unit="MB"
          icon={<HardDrive className="w-3.5 h-3.5 text-muted" />}
        />
        <GaugeRow
          label="PID Task Count"
          current={resources.pids}
          limit={resources.pids_limit}
          unit="pids"
          icon={<Server className="w-3.5 h-3.5 text-muted" />}
        />
      </div>

      <div className="mt-3 pt-2 border-t border-line text-[10px] font-mono text-muted text-right">
        Kernel cgroup-v2 enforcement active
      </div>
    </div>
  );
};
