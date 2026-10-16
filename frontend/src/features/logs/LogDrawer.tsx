import React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X, ArrowRight, ShieldAlert, Link2, FileCode } from 'lucide-react';
import { useUiStore } from '@/store/uiStore';
import { useLiveStore } from '@/store/liveStore';
import { DecisionBadge } from '@/components/DecisionBadge';
import { RiskMeter } from '@/components/RiskMeter';
import { HashChip } from '@/components/HashChip';
import { JsonView } from '@/components/JsonView';
import { ArgumentViewer } from './ArgumentViewer';

export const LogDrawer: React.FC = () => {
  const { selectedAuditId, isDrawerOpen, closeDrawer } = useUiStore();
  const entry = useLiveStore((s) => s.auditLogs.find((l) => l.id === selectedAuditId));

  if (!isDrawerOpen || !entry) return null;

  // Support both risk_score and score returned from backend
  const riskScore =
    entry.risk_score !== undefined && entry.risk_score !== null
      ? entry.risk_score
      : (entry as any).score !== undefined
      ? (entry as any).score
      : null;

  return (
    <Dialog.Root open={isDrawerOpen} onOpenChange={(open) => !open && closeDrawer()}>
      <Dialog.Portal>
        {/* Invisible overlay so user can still see underlying table */}
        <Dialog.Overlay className="fixed inset-0 z-40 bg-bg/40 backdrop-blur-[1px] transition-opacity" />

        <Dialog.Content
          className="fixed inset-y-0 right-0 z-50 w-full max-w-[520px] border-l border-line bg-surface p-6 shadow-2xl flex flex-col justify-between overflow-y-auto text-ink focus:outline-none animate-in slide-in-from-right duration-200"
        >
          <div className="space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between pb-4 border-b border-line">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs font-bold text-muted">ENTRY #{entry.id}</span>
                  <DecisionBadge decision={entry.decision} size="sm" />
                </div>
                <Dialog.Title className="text-lg font-bold text-ink">
                  Log Entry Structure
                </Dialog.Title>
                <Dialog.Description className="text-xs font-mono text-muted mt-0.5">
                  {new Date(entry.ts).toLocaleString()}
                </Dialog.Description>
              </div>

              <Dialog.Close asChild>
                <button
                  type="button"
                  className="p-1.5 rounded-lg border border-line text-muted hover:text-ink hover:bg-raised transition-colors focus-visible:ring-2 focus-visible:ring-accent"
                  aria-label="Close details drawer"
                >
                  <X className="w-4 h-4" />
                </button>
              </Dialog.Close>
            </div>

            {/* Core Metadata Grid */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-lg border border-line bg-raised/50">
                <span className="text-muted block text-[11px] mb-1">Tool Executed</span>
                <span className="font-mono font-semibold text-ink uppercase">{entry.tool}</span>
              </div>
              <div className="p-3 rounded-lg border border-line bg-raised/50">
                <span className="text-muted block text-[11px] mb-1">Policy Source</span>
                <span className="font-mono font-semibold text-ink uppercase">{entry.source}</span>
              </div>
              <div className="p-3 rounded-lg border border-line bg-raised/50">
                <span className="text-muted block text-[11px] mb-1">Rule ID</span>
                <span className="font-mono font-semibold text-accent">{entry.rule_id || 'DEFAULT-POLICY'}</span>
              </div>
              <div className="p-3 rounded-lg border border-line bg-raised/50">
                <span className="text-muted block text-[11px] mb-1">Prompt Guard 2 Risk</span>
                <RiskMeter score={riskScore} />
              </div>
            </div>

            {/* Policy Reason */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted mb-1.5 flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5" />
                Gate Enforcement Reason
              </h4>
              <div className="p-3 rounded-lg border border-line bg-raised/30 text-xs font-mono leading-relaxed text-ink">
                {entry.reason}
              </div>
            </div>

            {/* Executed Arguments (Human-readable + Decoded JSON + Raw) */}
            <ArgumentViewer rawArgs={entry.args} tool={entry.tool} />

            {/* Attacker Context (if present) */}
            {(entry.agent_thought || entry.user_input) && (
              <div className="space-y-3">
                {entry.user_input && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted mb-1.5">
                      User Prompt Context
                    </h4>
                    <div className="p-3 rounded-lg border border-line bg-raised/40 text-xs font-mono whitespace-pre-wrap break-all text-ink">
                      {entry.user_input}
                    </div>
                  </div>
                )}
                {entry.agent_thought && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted mb-1.5">
                      Agent Thought Stream
                    </h4>
                    <div className="p-3 rounded-lg border border-line bg-raised/40 text-xs font-mono whitespace-pre-wrap break-all text-ink">
                      {entry.agent_thought}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Hash Chain Linkage */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted mb-2 flex items-center gap-1.5">
                <Link2 className="w-3.5 h-3.5" />
                Cryptographic Audit Chain (SHA-256)
              </h4>
              <div className="p-3 rounded-lg border border-line bg-raised/50 space-y-2 text-xs">
                <div>
                  <span className="text-[11px] text-muted block mb-1">Previous Block Hash:</span>
                  <HashChip hash={entry.prev_hash} truncateLength={14} />
                </div>
                <div className="flex items-center justify-center text-muted">
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
                <div>
                  <span className="text-[11px] text-muted block mb-1">Current Entry Hash:</span>
                  <HashChip hash={entry.hash} truncateLength={14} />
                </div>
              </div>
            </div>

            {/* Raw JSON */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted mb-1.5 flex items-center gap-1.5">
                <FileCode className="w-3.5 h-3.5" />
                Raw Payload
              </h4>
              <JsonView data={entry} maxHeight="max-h-48" />
            </div>
          </div>

          <div className="pt-4 mt-6 border-t border-line flex justify-end">
            <button
              type="button"
              onClick={closeDrawer}
              className="px-4 py-2 text-xs font-medium rounded-lg border border-line bg-raised hover:bg-surface text-ink transition-colors"
            >
              Close Drawer
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
