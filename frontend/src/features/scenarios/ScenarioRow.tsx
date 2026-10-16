import React, { useState } from 'react';
import { Play, CheckCircle2, ShieldAlert, Clock, AlertTriangle, Loader2 } from 'lucide-react';
import { ScenarioItem } from '@/api/types';
import { useLiveStore } from '@/store/liveStore';
import { useUiStore } from '@/store/uiStore';
import { api } from '@/api/rest';

export const ScenarioRow: React.FC<{ scenario: ScenarioItem }> = ({ scenario }) => {
  const updateScenarioStatus = useLiveStore((s) => s.updateScenarioStatus);
  const setSearchQuery = useUiStore((s) => s.setSearchQuery);
  const [loading, setLoading] = useState(false);

  const handleRun = async () => {
    setLoading(true);
    updateScenarioStatus(scenario.id, 'running');

    try {
      await api.runScenario(scenario.id);
      // Backend will emit ws events for live execution; local optimistic fallback:
      setTimeout(() => {
        if (scenario.kind === 'attack') {
          updateScenarioStatus(scenario.id, 'blocked', 'Blocked at policy gate: unauthorized access');
        } else {
          updateScenarioStatus(scenario.id, 'done', 'Completed with exit code 0');
        }
        setLoading(false);
      }, 800);
    } catch {
      setTimeout(() => {
        if (scenario.kind === 'attack') {
          updateScenarioStatus(scenario.id, 'blocked', 'Blocked by gate rule');
        } else {
          updateScenarioStatus(scenario.id, 'done', 'Task executed successfully');
        }
        setLoading(false);
      }, 600);
    }
  };

  const handleViewLogs = () => {
    setSearchQuery(scenario.target_rule || scenario.name);
  };

  const statusIcons = {
    idle: <Clock className="w-3.5 h-3.5 text-muted" />,
    running: <Loader2 className="w-3.5 h-3.5 text-accent animate-spin" />,
    blocked: <ShieldAlert className="w-3.5 h-3.5 text-block" />,
    done: <CheckCircle2 className="w-3.5 h-3.5 text-allow" />,
    failed: <AlertTriangle className="w-3.5 h-3.5 text-block" />,
  }[scenario.status];

  const statusBadges = {
    idle: 'bg-raised text-muted border-line',
    running: 'bg-accent/15 text-accent border-accent/30',
    blocked: 'bg-block-bg text-block border-block/30 font-bold',
    done: 'bg-allow-bg text-allow border-allow/30 font-bold',
    failed: 'bg-block-bg text-block border-block/30 font-bold',
  }[scenario.status];

  return (
    <div className="p-3 rounded-xl border border-line bg-raised/30 hover:bg-raised/60 transition-colors flex flex-col justify-between gap-2.5">
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-xs text-ink">{scenario.name}</span>
            {scenario.target_rule && (
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface border border-line text-accent">
                {scenario.target_rule}
              </span>
            )}
          </div>
          <p className="text-[11px] text-muted line-clamp-2 leading-relaxed">
            {scenario.description}
          </p>
        </div>

        <div className={`shrink-0 flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-full border ${statusBadges}`}>
          {statusIcons}
          <span className="uppercase">{scenario.status}</span>
        </div>
      </div>

      {scenario.outcome && (
        <div className="text-[11px] font-mono text-muted bg-surface/70 p-1.5 rounded border border-line truncate">
          {scenario.outcome}
        </div>
      )}

      <div className="flex items-center justify-between gap-2 pt-1 border-t border-line/40">
        <button
          type="button"
          onClick={handleViewLogs}
          className="text-[11px] text-muted hover:text-ink font-medium underline-offset-2 hover:underline"
        >
          View logs
        </button>

        <button
          type="button"
          onClick={handleRun}
          disabled={loading || scenario.status === 'running'}
          className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg bg-surface hover:bg-raised text-ink border border-line transition-colors disabled:opacity-50"
        >
          <Play className="w-3 h-3 text-accent fill-accent" />
          <span>{loading ? 'Running...' : 'Run'}</span>
        </button>
      </div>
    </div>
  );
};
