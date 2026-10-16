import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Activity } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';
import { useThemeColors } from '@/theme/useThemeColors';

export const TimelineChart: React.FC = () => {
  const timelinePoints = useLiveStore((s) => s.timelinePoints);
  const colors = useThemeColors();

  return (
    <div className="flex flex-col h-full rounded-card border border-line bg-surface p-4">
      <div className="flex items-center justify-between pb-2 border-b border-line mb-3">
        <div className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-accent" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
            Tool Call Velocity & Decision Timeline
          </h3>
        </div>
        <div className="flex items-center gap-3 text-[11px] font-mono">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: colors.allow }} />
            <span className="text-ink">Allowed</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: colors.block }} />
            <span className="text-ink">Blocked</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: colors.ask }} />
            <span className="text-ink">Ask</span>
          </span>
        </div>
      </div>

      <div className="flex-1 w-full min-h-[160px]">
        {timelinePoints.length === 0 ? (
          <div className="h-full flex items-center justify-center text-muted text-xs font-mono">
            Awaiting streaming activity data...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={timelinePoints} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradAllow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors.allow} stopOpacity={0.35} />
                  <stop offset="95%" stopColor={colors.allow} stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="gradBlock" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors.block} stopOpacity={0.45} />
                  <stop offset="95%" stopColor={colors.block} stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="gradAsk" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors.ask} stopOpacity={0.35} />
                  <stop offset="95%" stopColor={colors.ask} stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={colors.line} strokeDasharray="3 3" opacity={0.6} />
              <XAxis
                dataKey="time"
                stroke={colors.muted}
                fontSize={10}
                tickLine={false}
                axisLine={{ stroke: colors.line }}
              />
              <YAxis
                stroke={colors.muted}
                fontSize={10}
                tickLine={false}
                axisLine={{ stroke: colors.line }}
                allowDecimals={false}
              />
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
              <Area
                type="monotone"
                dataKey="allowed"
                stroke={colors.allow}
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#gradAllow)"
                name="Allowed"
              />
              <Area
                type="monotone"
                dataKey="blocked"
                stroke={colors.block}
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#gradBlock)"
                name="Blocked"
              />
              <Area
                type="monotone"
                dataKey="ask"
                stroke={colors.ask}
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#gradAsk)"
                name="Ask"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};
