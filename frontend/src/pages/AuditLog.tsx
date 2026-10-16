import React from 'react';
import { Database } from 'lucide-react';
import { LogTable } from '@/features/logs/LogTable';
import { ChainCard } from '@/features/chain/ChainCard';
import { useLiveStore } from '@/store/liveStore';

export const AuditLog: React.FC = () => {
  const counts = useLiveStore((s) => s.counts);

  return (
    <div className="space-y-4 max-w-[1920px] mx-auto pb-10">
      <div className="flex items-center justify-between pb-3 border-b border-line">
        <div>
          <h2 className="text-base font-bold text-ink">Tamper-Evident Audit Ledger</h2>
          <p className="text-xs text-muted">
            Append-only, SHA-256 hash-chained log recording every agent tool invocation, decision, and risk score.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* Main Logs Table (col 9) */}
        <div className="lg:col-span-9 h-[640px]">
          <LogTable maxHeight="h-[550px]" />
        </div>

        {/* Chain Integrity & Verification Panel (col 3) */}
        <div className="lg:col-span-3 space-y-4">
          <ChainCard />

          <div className="rounded-card border border-line bg-surface p-4 space-y-3 card-hover">
            <div className="flex items-center gap-2 pb-2 border-b border-line">
              <Database className="w-4 h-4 text-accent" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
                Ledger Statistics
              </h3>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-line/40">
                <span className="text-muted">Total Recorded</span>
                <span className="font-mono font-bold text-ink">{counts.total}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-line/40">
                <span className="text-muted">Allowed</span>
                <span className="font-mono font-bold text-allow flex items-center gap-1.5">
                  <span>{counts.allow}</span>
                  {counts.total > 0 && (
                    <span className="text-[10px] font-normal px-1 rounded bg-allow-bg border border-allow/30">
                      {Math.round((counts.allow / counts.total) * 100)}%
                    </span>
                  )}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-line/40">
                <span className="text-muted">Blocked</span>
                <span className="font-mono font-bold text-block flex items-center gap-1.5">
                  <span>{counts.block}</span>
                  {counts.total > 0 && (
                    <span className="text-[10px] font-normal px-1 rounded bg-block-bg border border-block/30">
                      {Math.round((counts.block / counts.total) * 100)}%
                    </span>
                  )}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-muted">Human Approvals</span>
                <span className="font-mono font-bold text-ask flex items-center gap-1.5">
                  <span>{counts.ask}</span>
                  {counts.total > 0 && (
                    <span className="text-[10px] font-normal px-1 rounded bg-ask-bg border border-ask/30">
                      {Math.round((counts.ask / counts.total) * 100)}%
                    </span>
                  )}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
