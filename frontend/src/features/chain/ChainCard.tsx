import React, { useState } from 'react';
import { Link, ShieldCheck, ShieldAlert, AlertTriangle, RefreshCw } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';
import { HashChip } from '@/components/HashChip';
import { api } from '@/api/rest';

export const ChainCard: React.FC = () => {
  const chain = useLiveStore((s) => s.chain);
  const updateChainStatus = useLiveStore((s) => s.updateChainStatus);
  const [verifying, setVerifying] = useState(false);
  const [tampering, setTampering] = useState(false);

  const handleVerify = async () => {
    setVerifying(true);
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
      console.error('Failed to verify chain:', e);
    } finally {
      setVerifying(false);
    }
  };

  const handleTamperTest = async () => {
    setTampering(true);
    try {
      await api.tamperTest();
      // After tampering, re-verify to demonstrate red failure state
      const res = await api.verifyChain();
      updateChainStatus({
        ok: res.ok,
        entries: res.entries,
        head_hash: res.head_hash,
        last_verified: res.last_verified,
        first_broken_id: res.first_broken_id,
      });
    } catch (e) {
      console.error('Tamper demo failed:', e);
    } finally {
      setTampering(false);
    }
  };

  const handleRestoreChain = async () => {
    setVerifying(true);
    try {
      await api.clearAuditLogs();
      const res = await api.verifyChain();
      updateChainStatus({
        ok: res.ok,
        entries: res.entries,
        head_hash: res.head_hash,
        last_verified: res.last_verified,
        first_broken_id: undefined,
      });
    } catch (e) {
      console.error('Failed to reset ledger:', e);
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div
      className={`rounded-card border p-3 sm:p-3.5 flex flex-col justify-between h-full card-hover ${
        chain.ok ? 'border-line bg-surface' : 'border-block/80 bg-block-bg/25 shadow-sm shadow-block/10'
      }`}
    >
      <div className="space-y-1.5">
        <div className="flex items-center justify-between pb-1.5 border-b border-line mb-2">
          <div className="flex items-center gap-1.5">
            <Link className="w-3.5 h-3.5 text-accent shrink-0" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted truncate">
              Audit Chain Integrity
            </h3>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {chain.ok ? (
              <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-allow bg-allow-bg/60 border border-allow/30 px-1.5 py-0.5 rounded">
                <ShieldCheck className="w-3 h-3 text-allow" />
                CHAIN INTACT
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-block bg-block-bg border border-block/40 px-1.5 py-0.5 rounded animate-pulse">
                <ShieldAlert className="w-3 h-3 text-block" />
                TAMPER DETECTED
              </span>
            )}
          </div>
        </div>

        {!chain.ok && (
          <div className="p-2 rounded-md border border-block/50 bg-block-bg/40 text-[10px] font-mono text-block flex items-start gap-1.5 leading-snug">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold">Cryptographic Violation:</strong> Prev-hash mismatch at record #{chain.first_broken_id ?? '1'}. Ledger modified out-of-band!
            </div>
          </div>
        )}

        <div className="space-y-1 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-muted text-[10px]">Ledger Head:</span>
            <HashChip hash={chain.head_hash} truncateLength={6} />
          </div>

          <div className="flex items-center justify-between">
            <span className="text-muted text-[10px]">Blocks Verified:</span>
            <span className="font-mono font-semibold text-ink text-[10px] bg-raised px-1.5 py-0.2 rounded border border-line/40">
              {chain.entries} blocks
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-muted text-[10px]">Last Scanned:</span>
            <span className="font-mono text-muted text-[10px]">
              {new Date(chain.last_verified).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-2 pt-2 border-t border-line flex items-center justify-between gap-1.5">
        <button
          type="button"
          onClick={handleVerify}
          disabled={verifying}
          className="flex-1 flex items-center justify-center gap-1.5 py-1 px-2.5 rounded-lg border border-line bg-raised hover:bg-surface text-ink text-xs font-medium transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${verifying ? 'animate-spin text-accent' : ''}`} />
          <span>{verifying ? 'Verifying...' : 'Verify'}</span>
        </button>

        {chain.ok ? (
          <button
            type="button"
            onClick={handleTamperTest}
            disabled={tampering}
            title="Inject simulated modification to test tamper detection"
            className="text-[10px] font-mono px-2 py-1 rounded-lg border border-line hover:border-block text-muted hover:text-block transition-colors shrink-0"
          >
            {tampering ? 'Tampering...' : 'Simulate Tamper'}
          </button>
        ) : (
          <button
            type="button"
            onClick={handleRestoreChain}
            disabled={verifying}
            className="text-[10px] font-mono px-2 py-1 rounded-md border border-line hover:border-allow text-muted hover:text-allow transition-colors font-bold"
          >
            Reset Ledger
          </button>
        )}
      </div>
    </div>
  );
};
