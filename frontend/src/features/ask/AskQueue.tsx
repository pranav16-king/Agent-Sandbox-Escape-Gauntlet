import React, { useState, useEffect } from 'react';
import { UserCheck, Check, X, Clock, AlertTriangle } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';
import { RiskMeter } from '@/components/RiskMeter';
import { api } from '@/api/rest';
import { AskRequest } from '@/api/types';

interface AskItemCardProps {
  ask: AskRequest;
  onResolve: (id: number, outcome: 'approved' | 'denied' | 'timeout') => void;
}

const AskItemCard: React.FC<AskItemCardProps> = ({ ask, onResolve }) => {
  const [timeLeft, setTimeLeft] = useState(() => {
    const expiry = new Date(ask.expires_at).getTime();
    return Math.max(0, Math.floor((expiry - Date.now()) / 1000));
  });

  useEffect(() => {
    const timer = setInterval(() => {
      const expiry = new Date(ask.expires_at).getTime();
      const remaining = Math.max(0, Math.floor((expiry - Date.now()) / 1000));
      setTimeLeft(remaining);

      if (remaining <= 0) {
        clearInterval(timer);
        onResolve(ask.audit_id, 'timeout');
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [ask.expires_at, ask.audit_id, onResolve]);

  const handleApprove = async () => {
    try {
      await api.resolveAsk(ask.audit_id, 'approve');
    } catch {}
    onResolve(ask.audit_id, 'approved');
  };

  const handleDeny = async () => {
    try {
      await api.resolveAsk(ask.audit_id, 'deny');
    } catch {}
    onResolve(ask.audit_id, 'denied');
  };

  const mins = Math.floor(timeLeft / 60);
  const secs = timeLeft % 60;
  const timeFormatted = `${mins}:${secs < 10 ? '0' : ''}${secs}`;

  return (
    <div className="rounded-xl border border-ask/40 bg-ask-bg/20 p-3 space-y-2.5">
      <div className="flex items-center justify-between text-xs">
        <span className="font-mono font-bold text-ask uppercase">
          TOOL: {ask.tool}
        </span>
        <div className="flex items-center gap-1 font-mono text-muted text-[11px]">
          <Clock className="w-3 h-3 text-ask" />
          <span>Auto-deny in {timeFormatted}</span>
        </div>
      </div>

      <div className="p-2 rounded bg-surface border border-line text-xs font-mono break-all text-ink">
        {ask.args}
      </div>

      <div className="flex items-center justify-between text-xs">
        <span className="text-muted text-[11px] truncate max-w-[200px]" title={ask.reason}>
          {ask.reason}
        </span>
        <RiskMeter score={ask.risk_score} />
      </div>

      <div className="flex items-center gap-2 pt-1">
        <button
          type="button"
          onClick={handleApprove}
          className="flex-1 flex items-center justify-center gap-1 py-1.5 px-3 rounded-lg bg-allow text-white hover:opacity-90 font-semibold text-xs transition-opacity"
        >
          <Check className="w-3.5 h-3.5" />
          <span>Approve</span>
        </button>
        <button
          type="button"
          onClick={handleDeny}
          className="flex-1 flex items-center justify-center gap-1 py-1.5 px-3 rounded-lg bg-block text-white hover:opacity-90 font-semibold text-xs transition-opacity"
        >
          <X className="w-3.5 h-3.5" />
          <span>Deny</span>
        </button>
      </div>
    </div>
  );
};

export const AskQueue: React.FC = () => {
  const pendingAsks = useLiveStore((s) => s.pendingAsks);
  const resolveAsk = useLiveStore((s) => s.resolveAsk);

  return (
    <div className="rounded-card border border-line bg-surface p-4 flex flex-col justify-between h-full">
      <div className="flex items-center justify-between pb-2 border-b border-line mb-3">
        <div className="flex items-center gap-1.5">
          <UserCheck className="w-3.5 h-3.5 text-ask" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
            Pending Human Approvals
          </h3>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-ask-bg text-ask font-bold">
          {pendingAsks.length} PENDING
        </span>
      </div>

      <div className="space-y-3 overflow-y-auto max-h-[240px]">
        {pendingAsks.length === 0 ? (
          <div className="h-32 flex flex-col items-center justify-center text-muted text-xs text-center px-4">
            <Check className="w-6 h-6 mb-1 text-allow opacity-60" />
            <span>No pending tool actions require human clearance.</span>
          </div>
        ) : (
          pendingAsks.map((ask) => (
            <AskItemCard key={ask.audit_id} ask={ask} onResolve={resolveAsk} />
          ))
        )}
      </div>

      <div className="mt-3 pt-2 border-t border-line text-[11px] text-muted flex items-center gap-1.5 font-mono">
        <AlertTriangle className="w-3 h-3 text-ask" />
        <span>Fail-closed: Unapproved actions automatically default to block.</span>
      </div>
    </div>
  );
};
