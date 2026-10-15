import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { PieChart as PieIcon } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';
import { useThemeColors } from '@/theme/useThemeColors';

export const AttackDonut: React.FC = () => {
  const counts = useLiveStore((s) => s.counts);
  const colors = useThemeColors();

  const total = counts.allow + counts.block + counts.ask;

  const data = [
    { name: 'Allowed Actions', value: counts.allow || (total === 0 ? 1 : 0), color: colors.allow },
    { name: 'Blocked Exploits', value: counts.block, color: colors.block },
    { name: 'Human Cleared', value: counts.ask, color: colors.ask },
  ].filter((d) => d.value > 0);

  const blockRate = total > 0 ? Math.round((counts.block / total) * 100) : 0;

  return (
    <div className="flex flex-col h-full rounded-card border border-line bg-surface p-4 justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-line mb-2">
        <div className="flex items-center gap-1.5">
          <PieIcon className="w-3.5 h-3.5 text-accent" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
            Decision Distribution
          </h3>
        </div>
        <span className="text-[11px] font-mono text-muted">
          {total} evaluated
        </span>
      </div>

      <div className="relative flex-1 min-h-[140px] flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              innerRadius={44}
              outerRadius={62}
              paddingAngle={4}
              dataKey="value"
              stroke={colors.surface}
              strokeWidth={2}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: colors.surface,
                borderColor: colors.line,
                borderRadius: '8px',
                color: colors.text,
                fontSize: '11px',
                fontFamily: 'monospace',
              }}
            />
          </PieChart>
        </ResponsiveContainer>

        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-xl font-bold font-mono text-ink leading-none">
            {blockRate}%
          </span>
          <span className="text-[9px] font-mono text-muted uppercase mt-0.5">
            Blocked
          </span>
        </div>
      </div>

      <div className="pt-2 border-t border-line flex items-center justify-around text-[11px] font-mono">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: colors.allow }} />
          <span className="text-muted">Allow: <strong className="text-ink">{counts.allow}</strong></span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: colors.block }} />
          <span className="text-muted">Block: <strong className="text-ink">{counts.block}</strong></span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: colors.ask }} />
          <span className="text-muted">Ask: <strong className="text-ink">{counts.ask}</strong></span>
        </div>
      </div>
    </div>
  );
};
