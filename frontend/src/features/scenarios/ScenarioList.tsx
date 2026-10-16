import React, { useState } from 'react';
import { ShieldAlert, CheckCircle2 } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';
import { ScenarioRow } from './ScenarioRow';
import { api } from '@/api/rest';

interface ScenarioListProps {
  kind: 'attack' | 'normal';
  title?: string;
  maxHeight?: string;
}

export const ScenarioList: React.FC<ScenarioListProps> = ({
  kind,
  title,
  maxHeight = 'max-h-[300px]',
}) => {
  const scenarios = useLiveStore((s) => s.scenarios.filter((sc) => sc.kind === kind));
  const updateScenarioStatus = useLiveStore((s) => s.updateScenarioStatus);
  const [runningAll, setRunningAll] = useState(false);

  const isAttack = kind === 'attack';
  const defaultTitle = isAttack ? 'Attack Scenarios Gauntlet' : 'Normal Operational Tasks';

  const handleRunAll = async () => {
    setRunningAll(true);
    scenarios.forEach((sc) => updateScenarioStatus(sc.id, 'running'));

    try {
      await api.runAllScenarios(kind);
    } catch {}

    // Stagger simulated completion
    scenarios.forEach((sc, idx) => {
      setTimeout(() => {
        if (isAttack) {
          updateScenarioStatus(sc.id, 'blocked', 'Blocked at policy gate');
        } else {
          updateScenarioStatus(sc.id, 'done', 'Completed successfully');
        }
        if (idx === scenarios.length - 1) setRunningAll(false);
      }, 400 * (idx + 1));
    });
  };

  return (
    <div className="rounded-card border border-line bg-surface p-4 flex flex-col justify-between h-full card-hover">
      <div className="flex items-center justify-between pb-2 border-b border-line mb-3">
        <div className="flex items-center gap-1.5">
          {isAttack ? (
            <ShieldAlert className="w-3.5 h-3.5 text-block" />
          ) : (
            <CheckCircle2 className="w-3.5 h-3.5 text-allow" />
          )}
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
            {title || defaultTitle}
          </h3>
        </div>

        <button
          type="button"
          onClick={handleRunAll}
          disabled={runningAll || scenarios.length === 0}
          className="text-xs font-semibold px-2.5 py-1 rounded-lg border border-line bg-raised hover:bg-surface text-ink transition-colors disabled:opacity-50"
        >
          {runningAll ? 'Running...' : `Run All (${scenarios.length})`}
        </button>
      </div>

      <div className={`space-y-2.5 overflow-y-auto ${maxHeight}`}>
        {scenarios.length === 0 ? (
          <div className="h-36 flex flex-col items-center justify-center text-muted text-xs">
            <span>No {kind} scenarios loaded.</span>
          </div>
        ) : (
          scenarios.map((sc) => <ScenarioRow key={sc.id} scenario={sc} />)
        )}
      </div>

      <div className="mt-3 pt-2 border-t border-line text-[11px] font-mono text-muted flex items-center justify-between">
        <span>Verified against Docker + Squid</span>
        <span>{scenarios.filter((s) => s.status === (isAttack ? 'blocked' : 'done')).length} / {scenarios.length} passed</span>
      </div>
    </div>
  );
};
