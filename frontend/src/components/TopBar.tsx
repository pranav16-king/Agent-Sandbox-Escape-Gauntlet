import React from 'react';
import { Shield, ShieldOff, Sparkles, ZoomIn, ZoomOut, Menu } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';
import { useUiStore } from '@/store/uiStore';
import { useTheme } from '@/theme/ThemeProvider';
import { ThemeSwitcher } from './ThemeSwitcher';
import { ConnectionDot } from './ConnectionDot';

export const TopBar: React.FC = () => {
  const sandbox = useLiveStore((s) => s.system.sandbox);
  const connectionStatus = useLiveStore((s) => s.connectionStatus);
  const retryCount = useLiveStore((s) => s.retryCount);
  const setShowSandboxConfirm = useUiStore((s) => s.setShowSandboxConfirm);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const { largeMode, setLargeMode } = useTheme();

  return (
    <header className="shrink-0 sticky top-0 z-30 h-14 border-b border-line bg-surface/90 backdrop-blur-md px-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label="Toggle navigation menu"
          className="lg:hidden p-1.5 rounded-lg border border-line text-muted hover:text-ink hover:bg-raised transition-colors"
        >
          <Menu className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center text-on-accent font-bold text-sm shadow-sm">
            SX
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-ink leading-tight">
              sandboxX
            </h1>
            <span className="text-[10px] font-mono text-muted block -mt-0.5">
              Host Security Gateway
            </span>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 ml-4 pl-4 border-l border-line text-xs font-mono text-muted">
          <Sparkles className="w-3.5 h-3.5 text-accent" />
          <span>Agent: <strong className="text-ink">Qwen3 4B (Ollama)</strong></span>
          <span className="text-muted/60">|</span>
          <span>Shield: <strong className="text-ink">Prompt Guard 2 (86M)</strong></span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Connection status */}
        <ConnectionDot status={connectionStatus} retryCount={retryCount} />

        {/* Large mode toggle for projectors / demo screens */}
        <button
          type="button"
          onClick={() => setLargeMode(!largeMode)}
          aria-label={largeMode ? 'Standard font size' : 'Large projector font size'}
          title={largeMode ? 'Switch to Standard font size' : 'Switch to Large font size (16px) for projector'}
          className={`hidden md:flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-mono rounded-lg border border-line transition-colors ${
            largeMode ? 'bg-raised text-accent font-bold' : 'bg-surface hover:bg-raised text-muted hover:text-ink'
          }`}
        >
          {largeMode ? <ZoomOut className="w-3.5 h-3.5" /> : <ZoomIn className="w-3.5 h-3.5" />}
          <span>{largeMode ? 'Large ON' : '16px'}</span>
        </button>

        {/* Theme Switcher */}
        <ThemeSwitcher />

        {/* Sandbox ON/OFF Toggle */}
        <button
          type="button"
          onClick={() => setShowSandboxConfirm(true)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-bold tracking-wider transition-all select-none border ${
            sandbox === 'on'
              ? 'bg-allow-bg text-allow border-allow/40 hover:bg-allow/20'
              : 'bg-block text-white border-block hover:opacity-90 animate-pulse'
          }`}
          title="Toggle hardened sandbox execution"
        >
          {sandbox === 'on' ? (
            <>
              <Shield className="w-3.5 h-3.5 stroke-[2.5]" />
              <span>SANDBOX ON</span>
            </>
          ) : (
            <>
              <ShieldOff className="w-3.5 h-3.5 stroke-[2.5]" />
              <span>SANDBOX OFF</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
};
