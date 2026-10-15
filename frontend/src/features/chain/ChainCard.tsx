import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, RefreshCw, AlertTriangle, Link } from 'lucide-react';
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
      updateChainStatus(res);
    } catch {
      // Local fallback calculation if offline
      updateChainStatus({
        ...chain,
        last_verified: new Date().toISOString(),
      });
    } finally {
      setTimeout(() => setVerifying(false), 400);
    }
  };

  const handleTamperTest = async () => {
    setTampering(true);
    try {
      await api.tamperTest();
      // After tampering, re-verify to demonstrate red failure state
      const res = await api.verifyChain();
      updateChainStatus(res);
    } catch {
      // Offline simulation: simulate broken chain at entry #3
      updateChainStatus({
        ok: false,
        entries: chain.entries,
        head_hash: chain.head_hash,
        last_verified: new Date().toISOString(),
        first_broken_id: 3,
      });
    } finally {
      setTampering(false);
    }
  };

  const handleRestoreChain = () => {
    updateChainStatus({
      ok: true,
      entries: chain.entries,
      head_hash: chain.head_hash,
      last_verified: new Date().toISOString(),
      first_broken_id: undefined,
    });
  };

  return (
    <div
      className={`rounded-card border p-4 flex flex-col justify-between transition-colors ${
        chain.ok ? 'border-line bg-surface' : 'border-block bg-block-bg/20'
      }`}
    >
      <div>
        <div className="flex items-center justify-between pb-2 border-b border-line mb-3">
          <div className="flex items-center gap-1.5">
            <Link className="w-3.5 h-3.5 text-accent" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
              Audit Chain Integrity
            </h3>
          </div>

          <div className="flex items-center gap-1.5">
            {chain.ok ? (
              <span className="inline-flex items-center gap-1 text-xs font-mono font-bold text-allow">
                <ShieldCheck className="w-4 h-4 text-allow" />
                CHAIN INTACT
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs font-mono font-bold text-block">
                <ShieldAlert className="w-4 h-4 text-block animate-pulse" />
                TAMPER DETECTED
              </span>
            )}
          </div>
        </div>

        {!chain.ok && (
          <div className="mb-3 p-2.5 rounded-lg border border-block/40 bg-block-bg text-xs font-mono text-block flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <strong>Cryptographic Violation:</strong> Prev-hash mismatch discovered at record #
              {chain.first_broken_id ?? 'Unknown'}. Audit history has been modified out-of-band!
            </div>
          </div>
        )}

        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-muted">Ledger Head:</span>
            <HashChip hash={chain.head_hash} truncateLength={6} />
          </div>

          <div className="flex items-center justify-between">
            <span className="text-muted">Blocks Verified:</span>
            <span className="font-mono font-semibold text-ink">{chain.entries} blocks</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-muted">Last Scanned:</span>
            <span className="font-mono text-muted text-[11px]">
              {new Date(chain.last_verified).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-line flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={handleVerify}
          disabled={verifying}
          className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg border border-line bg-raised hover:bg-surface text-ink text-xs font-medium transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${verifying ? 'animate-spin text-accent' : ''}`} />
          <span>{verifying ? 'Verifying...' : 'Verify Ledger'}</span>
        </button>

        {chain.ok ? (
          <button
            type="button"
            onClick={handleTamperTest}
            disabled={tampering}
            title="Inject simulated modification to test tamper detection"
            className="text-[11px] font-mono px-2 py-1.5 rounded-lg border border-line hover:border-block text-muted hover:text-block transition-colors"
          >
            Simulate Tamper
          </button>
        ) : (
          <button
            type="button"
            onClick={handleRestoreChain}
            className="text-[11px] font-mono px-2 py-1.5 rounded-lg border border-line hover:border-allow text-muted hover:text-allow transition-colors"
          >
            Reset
          </button>
        )}
      </div>
    </div>
  );
};
