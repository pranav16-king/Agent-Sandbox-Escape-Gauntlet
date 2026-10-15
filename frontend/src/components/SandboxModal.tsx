import React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { AlertTriangle, ShieldOff, Shield } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';
import { useUiStore } from '@/store/uiStore';
import { api } from '@/api/rest';

export const SandboxModal: React.FC = () => {
  const { showSandboxConfirm, setShowSandboxConfirm } = useUiStore();
  const sandbox = useLiveStore((s) => s.system.sandbox);
  const setSandboxMode = useLiveStore((s) => s.setSandboxMode);

  const isTurningOff = sandbox === 'on';

  const handleConfirm = async () => {
    const nextMode = isTurningOff ? 'off' : 'on';
    try {
      await api.setSandboxMode(nextMode, true);
    } catch {}
    setSandboxMode(nextMode);
    setShowSandboxConfirm(false);
  };

  return (
    <Dialog.Root open={showSandboxConfirm} onOpenChange={setShowSandboxConfirm}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-full max-w-md rounded-2xl border border-line bg-surface p-6 shadow-2xl text-ink">
          <div className="flex items-center gap-3 mb-4">
            <div className={`p-3 rounded-xl ${isTurningOff ? 'bg-block-bg text-block' : 'bg-allow-bg text-allow'}`}>
              {isTurningOff ? <ShieldOff className="w-6 h-6" /> : <Shield className="w-6 h-6" />}
            </div>
            <div>
              <Dialog.Title className="text-base font-bold text-ink">
                {isTurningOff ? 'Disable Host Sandbox?' : 'Re-enable Host Sandbox'}
              </Dialog.Title>
              <Dialog.Description className="text-xs text-muted mt-0.5">
                {isTurningOff
                  ? 'Turning the sandbox OFF disables protection. Use only for demo comparison.'
                  : 'Re-activates all kernel containment, cgroups, and Squid proxy boundaries.'}
              </Dialog.Description>
            </div>
          </div>

          {isTurningOff && (
            <div className="p-3 rounded-xl border border-block/40 bg-block-bg/30 text-xs text-block mb-5 space-y-1 font-mono">
              <div className="flex items-center gap-1.5 font-bold">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>CRITICAL SECURITY WARNING:</span>
              </div>
              <p>
                In OFF mode, agent commands run unsandboxed. Host filesystem escape and unverified outbound egress will be permitted.
              </p>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setShowSandboxConfirm(false)}
              className="px-4 py-2 text-xs font-semibold rounded-lg border border-line bg-raised hover:bg-surface text-ink transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              className={`px-4 py-2 text-xs font-semibold rounded-lg text-white transition-opacity hover:opacity-90 ${
                isTurningOff ? 'bg-block' : 'bg-allow'
              }`}
            >
              {isTurningOff ? 'Yes, Disable Sandbox' : 'Enable Sandbox'}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
