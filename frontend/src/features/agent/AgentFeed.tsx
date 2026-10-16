import React, { useEffect, useRef, useState } from 'react';
import { Bot, User, ArrowDown } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';

export interface AgentFeedProps {
  maxHeight?: string;
  allowExpand?: boolean;
  defaultHeight?: 'normal' | 'medium' | 'tall';
}

export const AgentFeed: React.FC<AgentFeedProps> = ({
  maxHeight,
  allowExpand = true,
  defaultHeight = 'medium',
}) => {
  const agentMessages = useLiveStore((s) => s.agentMessages);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isScrolledUp, setIsScrolledUp] = useState(false);
  const [heightMode, setHeightMode] = useState<'normal' | 'medium' | 'tall'>(() => {
    try {
      const saved = localStorage.getItem('sandboxx_feed_height') as 'normal' | 'medium' | 'tall';
      if (saved && ['normal', 'medium', 'tall'].includes(saved)) return saved;
    } catch {}
    return defaultHeight;
  });

  const handleSetHeightMode = (mode: 'normal' | 'medium' | 'tall') => {
    setHeightMode(mode);
    try {
      localStorage.setItem('sandboxx_feed_height', mode);
    } catch {}
  };

  const heightClass = maxHeight || {
    normal: 'min-h-[380px] h-[380px]',
    medium: 'min-h-[500px] h-[500px]',
    tall: 'min-h-[680px] h-[680px]',
  }[heightMode];

  // Auto-scroll logic with smooth behavior
  useEffect(() => {
    if (!isScrolledUp && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [agentMessages, isScrolledUp]);

  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const distanceToBottom = scrollHeight - scrollTop - clientHeight;
    setIsScrolledUp(distanceToBottom > 40);
  };

  const scrollToBottom = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: 'smooth',
      });
      setIsScrolledUp(false);
    }
  };

  return (
    <div
      className={`relative flex flex-col rounded-card border border-line bg-surface overflow-hidden transition-all duration-200 card-hover ${heightClass}`}
    >
      <div className="p-3 border-b border-line flex items-center justify-between bg-raised/30 shrink-0">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-allow animate-pulse" />
          <Bot className="w-4 h-4 text-accent" />
          <h3 className="text-xs font-semibold text-ink uppercase tracking-wider">
            Live Agent Activity Stream
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-raised border border-line/60 text-muted">
            Qwen3 4B
          </span>
          <span className="text-[11px] font-mono text-muted hidden sm:inline">
            {agentMessages.length} events logged
          </span>

          {allowExpand && (
            <div className="flex items-center gap-1 bg-raised/70 p-0.5 rounded-lg border border-line/60">
              {(['normal', 'medium', 'tall'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => handleSetHeightMode(m)}
                  className={`px-1.5 py-0.5 rounded text-[10px] font-mono transition-colors ${
                    heightMode === m
                      ? 'bg-accent text-on-accent font-bold shadow-xs'
                      : 'text-muted hover:text-ink'
                  }`}
                  title={`Set section height to ${m === 'normal' ? '380px' : m === 'medium' ? '500px' : '680px'}`}
                >
                  {m === 'normal' ? '380px' : m === 'medium' ? '500px' : '680px'}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 min-h-0 p-3.5 space-y-3 overflow-y-auto text-xs leading-relaxed"
      >
        {agentMessages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-muted text-xs p-6 text-center">
            <div className="w-10 h-10 rounded-full bg-raised/70 border border-line flex items-center justify-center mb-2 text-accent">
              <Bot className="w-5 h-5 opacity-70" />
            </div>
            <span className="font-semibold text-ink">Awaiting Agent Activity</span>
            <span className="text-[11px] text-muted mt-0.5">
              Run an attack scenario from the gauntlet or send a task in Live Agent workbench.
            </span>
          </div>
        ) : (
          agentMessages.map((msg, idx) => {
            const isAgent = msg.role === 'agent';
            return (
              <div
                key={msg.id || idx}
                className={`flex gap-2.5 ${isAgent ? 'items-start' : 'items-start flex-row-reverse'}`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 border border-line ${
                    isAgent ? 'bg-raised text-accent' : 'bg-accent text-on-accent'
                  }`}
                >
                  {isAgent ? <Bot className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
                </div>

                <div
                  className={`max-w-[85%] rounded-xl p-3 border border-line ${
                    isAgent ? 'bg-raised/40 text-ink' : 'bg-raised/70 text-ink'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-[10px] font-semibold text-muted uppercase">
                      {isAgent ? 'LLM Agent' : 'User / Scenario Harness'}
                    </span>
                    {msg.ts && (
                      <span className="text-[10px] font-mono text-muted">
                        {new Date(msg.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    )}
                  </div>

                  {/* Render plain text safely */}
                  <div className="whitespace-pre-wrap font-mono text-xs text-ink break-words">
                    {msg.text}
                  </div>
                </div>
              </div>
            );
          })
        )}
        {/* Dedicated buffer so the final message is never clipped at the bottom after scrolling */}
        <div className="h-6 shrink-0" aria-hidden="true" />
      </div>

      {/* Jump to latest button */}
      {isScrolledUp && (
        <button
          type="button"
          onClick={scrollToBottom}
          className="absolute bottom-3 right-3 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-accent text-on-accent font-semibold text-xs shadow-lg transition-transform hover:scale-105 active:scale-95"
        >
          <ArrowDown className="w-3.5 h-3.5" />
          <span>Jump to latest</span>
        </button>
      )}
    </div>
  );
};
