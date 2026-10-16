import React from 'react';
import { KpiStrip } from '@/features/kpi/KpiStrip';
import { AgentFeed } from '@/features/agent/AgentFeed';
import { PipelineFlow } from '@/features/pipeline/PipelineFlow';
import { SystemStatus } from '@/features/runtime/SystemStatus';
import { ChainCard } from '@/features/chain/ChainCard';
import { TimelineChart } from '@/features/charts/TimelineChart';
import { AttackDonut } from '@/features/charts/AttackDonut';
import { LogTable } from '@/features/logs/LogTable';
import { AskQueue } from '@/features/ask/AskQueue';
import { NetworkTable } from '@/features/runtime/NetworkTable';
import { ScenarioList } from '@/features/scenarios/ScenarioList';
import { ResourceGauges } from '@/features/runtime/ResourceGauges';

export const Dashboard: React.FC = () => {
  return (
    <div className="space-y-4 max-w-[1920px] mx-auto pb-10">
      {/* Row 1: KPI Strip (6 cards) */}
      <section aria-label="Key Performance Indicators">
        <KpiStrip />
      </section>

      {/* Row 2: Live Agent Activity (col 5) | Pipeline Flow (col 4) | System Status + Chain Card (col 3) */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
        <div className="lg:col-span-5 min-h-[380px] flex flex-col">
          <AgentFeed maxHeight="h-[310px]" />
        </div>
        <div className="lg:col-span-4 min-h-[380px] flex flex-col">
          <PipelineFlow />
        </div>
        <div className="lg:col-span-3 flex flex-col gap-3 min-h-[380px]">
          <div className="flex-1 min-h-0">
            <SystemStatus />
          </div>
          <div className="flex-1 min-h-0">
            <ChainCard />
          </div>
        </div>
      </section>

      {/* Row 3: Tool Call Timeline (col 8) | Attack vs Normal (col 4) */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
        <div className="lg:col-span-8 min-h-[260px] flex flex-col">
          <TimelineChart />
        </div>
        <div className="lg:col-span-4 min-h-[260px] flex flex-col">
          <AttackDonut />
        </div>
      </section>

      {/* Row 4: Live Logs Table (col 8) | Ask Queue + Network Activity (col 4) */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
        <div className="lg:col-span-8 min-h-[380px] flex flex-col">
          <LogTable maxHeight="h-[290px]" />
        </div>
        <div className="lg:col-span-4 flex flex-col gap-4 min-h-[380px]">
          <div className="flex-1 min-h-0">
            <AskQueue />
          </div>
          <div className="flex-1 min-h-0">
            <NetworkTable maxHeight="max-h-[120px]" />
          </div>
        </div>
      </section>

      {/* Row 5: Attack Scenarios (col 4) | Normal Tasks (col 4) | Container Resources (col 4) */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
        <div className="lg:col-span-4 min-h-[340px] flex flex-col">
          <ScenarioList kind="attack" maxHeight="max-h-[240px]" />
        </div>
        <div className="lg:col-span-4 min-h-[340px] flex flex-col">
          <ScenarioList kind="normal" maxHeight="max-h-[240px]" />
        </div>
        <div className="lg:col-span-4 min-h-[340px] flex flex-col">
          <ResourceGauges />
        </div>
      </section>
    </div>
  );
};
