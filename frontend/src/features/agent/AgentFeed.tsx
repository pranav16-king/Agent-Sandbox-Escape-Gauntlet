import React, { useEffect, useRef, useState } from 'react';
import { Bot, User, ArrowDown } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';

export const AgentFeed: React.FC<{ maxHeight?: string }> = ({ maxHeight = 'h-[320px]' }) => {
  const agentMessages = useLiveStore((s) => s.agentMessages);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isScrolledUp, setIsScrolledUp] = useState(false);

  // Auto-scroll logic
  useEffect(() => {
    if (!isScrolledUp && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
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
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
      setIsScrolledUp(false);
    }
  };

  return (
    <div className="relative flex flex-col h-full rounded-card border border-line bg-surface overflow-hidden">
      <div className="p-3 border-b border-line flex items-center justify-between bg-raised/30">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-accent" />
          <h3 className="text-xs font-semibold text-ink uppercase tracking-wider">
            Live Agent Activity Stream
          </h3>
        </div>
        <span className="text-[11px] font-mono text-muted">
          {agentMessages.length} events logged
        </span>
      </div>

      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className={`flex-1 p-3.5 space-y-3 overflow-y-auto ${maxHeight} text-xs leading-relaxed`}
      >
        {agentMessages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-muted text-xs">
            <Bot className="w-8 h-8 mb-2 opacity-40 text-muted" />
            <span>Awaiting agent task instructions or scenario execution.</span>
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
