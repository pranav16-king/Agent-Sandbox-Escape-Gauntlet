import React from 'react';
import { ShieldOff, AlertTriangle } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';
import { useUiStore } from '@/store/uiStore';

export const SandboxBanner: React.FC = () => {
  const sandbox = useLiveStore((s) => s.system.sandbox);
  const setShowSandboxConfirm = useUiStore((s) => s.setShowSandboxConfirm);

  if (sandbox === 'on') return null;

  return (
    <div
      role="alert"
      className="w-full bg-block text-white px-4 py-2 flex items-center justify-between text-xs font-semibold shadow-md z-30 select-none animate-in fade-in"
    >
      <div className="flex items-center gap-2">
        <ShieldOff className="w-4 h-4 shrink-0" />
        <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-white" />
        <span className="font-mono tracking-wide uppercase">
          SANDBOX PROTECTION IS DISABLED (OFF MODE)
        </span>
        <span className="hidden md:inline font-normal text-white/90">
          — Host isolation bypassed for attack escape demonstration. Host is exposed to malicious payload execution.
        </span>
      </div>

      <button
        type="button"
        onClick={() => setShowSandboxConfirm(true)}
        className="px-3 py-1 rounded bg-white text-block hover:bg-neutral-100 font-bold text-xs uppercase tracking-wider transition-colors shrink-0 shadow-sm"
      >
        Re-Enable Sandbox
      </button>
    </div>
  );
};
