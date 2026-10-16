import React from 'react';
import { Swords, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { ScenarioList } from '@/features/scenarios/ScenarioList';
import { useLiveStore } from '@/store/liveStore';

export const Scenarios: React.FC = () => {
  const counts = useLiveStore((s) => s.counts);

  return (
    <div className="space-y-4 max-w-[1920px] mx-auto pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-line gap-3">
        <div>
          <h2 className="text-base font-bold text-ink flex items-center gap-2">
            <Swords className="w-4 h-4 text-accent" />
            Gauntlet Evaluation Suite
          </h2>
          <p className="text-xs text-muted">
            Benchmark adversarial escape attempts against normal developer tasks to evaluate containment & utility.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border border-block/30 bg-block-bg text-block text-xs font-mono font-bold">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Attacks Blocked: {counts.attacks_blocked}</span>
          </div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border border-allow/30 bg-allow-bg text-allow text-xs font-mono font-bold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Tasks Passed: {counts.tasks_completed}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        {/* Attack Scenarios */}
        <div className="h-[600px]">
          <ScenarioList
            kind="attack"
            title="Adversarial Attack Scenarios (Red Team Gauntlet)"
            maxHeight="max-h-[500px]"
          />
        </div>

        {/* Normal Benchmark Tasks */}
        <div className="h-[600px]">
          <ScenarioList
            kind="normal"
            title="Standard Developer Tasks (Green Team Baseline)"
            maxHeight="max-h-[500px]"
          />
        </div>
      </div>
    </div>
  );
};
