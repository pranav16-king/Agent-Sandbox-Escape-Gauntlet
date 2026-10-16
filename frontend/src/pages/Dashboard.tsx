import React, { useState } from 'react';
import { ShieldCheck, Swords, RefreshCw, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useLiveStore } from '@/store/liveStore';
import { api } from '@/api/rest';
import { KpiStrip } from '@/features/kpi/KpiStrip';
import { AgentFeed } from '@/features/agent/AgentFeed';
import { PipelineFlow } from '@/features/pipeline/PipelineFlow';
import { ChainCard } from '@/features/chain/ChainCard';
import { TimelineChart } from '@/features/charts/TimelineChart';
import { AttackDonut } from '@/features/charts/AttackDonut';
import { LogTable } from '@/features/logs/LogTable';
import { AskQueue } from '@/features/ask/AskQueue';
import { NetworkTable } from '@/features/runtime/NetworkTable';
import { ScenarioList } from '@/features/scenarios/ScenarioList';
import { ResourceGauges } from '@/features/runtime/ResourceGauges';

export const Dashboard: React.FC = () => {
  const scenarios = useLiveStore((s) => s.scenarios);
  const updateScenarioStatus = useLiveStore((s) => s.updateScenarioStatus);
  const updateChainStatus = useLiveStore((s) => s.updateChainStatus);
  const workspace = useLiveStore((s) => s.workspace);
  const [runningGauntlet, setRunningGauntlet] = useState(false);
  const [verifyingChain, setVerifyingChain] = useState(false);

  const handleRunGauntlet = async () => {
    setRunningGauntlet(true);
    const attackScenarios = scenarios.filter((s) => s.kind === 'attack');
    attackScenarios.forEach((sc) => updateScenarioStatus(sc.id, 'running'));

    try {
      await api.runAllScenarios('attack');
    } catch {}

    attackScenarios.forEach((sc, idx) => {
      setTimeout(() => {
        updateScenarioStatus(sc.id, 'blocked', 'Blocked at policy gate: unauthorized access');
        if (idx === attackScenarios.length - 1) setRunningGauntlet(false);
      }, 400 * (idx + 1));
    });
  };

  const handleQuickVerify = async () => {
    setVerifyingChain(true);
    try {
      const res = await api.verifyChain();
      updateChainStatus({
        ok: res.ok,
        entries: res.entries,
        head_hash: res.head_hash,
        last_verified: res.last_verified,
        first_broken_id: res.first_broken_id,
      });
    } catch (e) {
      console.error(e);
    } finally {
      setTimeout(() => setVerifyingChain(false), 500);
    }
  };

  return (
    <div className="space-y-4 max-w-[1920px] mx-auto pb-10">
      {/* Executive Overview Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-line">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base sm:text-lg font-bold tracking-tight text-ink">
              Host Gateway Security Operations Center
            </h2>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-allow-bg text-allow border border-allow/30">
              <span className="w-1.5 h-1.5 rounded-full bg-allow animate-pulse" />
              LIVE TELEMETRY
            </span>
          </div>
          <p className="text-xs text-muted mt-0.5">
            Intercepting unprivileged AI agent tool calls in <strong className="font-mono text-ink font-semibold">{workspace?.name || 'workspace'}</strong>, evaluating OPA policies, and cryptographically sealing audit entries.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap shrink-0">
          <button
            type="button"
            onClick={handleRunGauntlet}
            disabled={runningGauntlet}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent text-on-accent text-xs font-semibold shadow-sm hover:opacity-90 transition-opacity disabled:opacity-50"
            title="Execute entire red-team attack gauntlet"
          >
            {runningGauntlet ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Swords className="w-3.5 h-3.5" />
            )}
            <span>{runningGauntlet ? 'Gauntlet Running...' : 'Run Attack Gauntlet'}</span>
          </button>

          <button
            type="button"
            onClick={handleQuickVerify}
            disabled={verifyingChain}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-line bg-surface hover:bg-raised text-ink text-xs font-medium transition-colors disabled:opacity-50"
            title="Verify SHA-256 HMAC Merkle chain integrity"
          >
            <ShieldCheck className={`w-3.5 h-3.5 text-allow ${verifyingChain ? 'animate-spin' : ''}`} />
            <span>{verifyingChain ? 'Verifying...' : 'Verify Ledger'}</span>
          </button>

          <Link
            to="/agent"
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-line bg-surface hover:bg-raised text-muted hover:text-ink text-xs font-medium transition-colors"
          >
            <span>Live Agent</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>

      {/* Row 1: KPI Strip (6 cards) */}
      <section aria-label="Key Performance Indicators">
        <KpiStrip />
      </section>

      {/* Row 2: Live Agent Activity (col 5) | Pipeline Flow (col 4) | Pending Approvals + Chain Card (col 3) */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
        <div className="lg:col-span-5 min-h-[480px] flex flex-col">
          <AgentFeed />
        </div>
        <div className="lg:col-span-4 min-h-[480px] flex flex-col">
          <PipelineFlow />
        </div>
        <div className="lg:col-span-3 flex flex-col gap-3 min-h-[480px]">
          <div className="flex-1 min-h-0">
            <AskQueue />
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

      {/* Row 4: Live Logs Table (col 8) | Controlled Egress Network Activity (col 4) */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
        <div className="lg:col-span-8 min-h-[380px] flex flex-col">
          <LogTable maxHeight="h-[290px]" />
        </div>
        <div className="lg:col-span-4 min-h-[380px] flex flex-col">
          <NetworkTable maxHeight="max-h-[300px]" />
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
