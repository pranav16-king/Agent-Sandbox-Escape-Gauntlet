import React, { useEffect, useRef, useState } from 'react';
import { Bot, User, ArrowDown, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';
import { AgentMessage } from '@/api/types';

interface MessageVerdict {
  decision: 'allow' | 'block' | 'ask' | null;
  ruleId?: string;
  reason?: string;
}

const getMessageVerdict = (msg: AgentMessage, isLastAgentMsg: boolean, latestLog: any): MessageVerdict => {
  // 1. Explicit decision on the message object
  if (msg.decision) {
    return {
      decision: msg.decision,
      ruleId: msg.rule_id,
      reason: msg.reason,
    };
  }

  const text = msg.text || '';

  // 2. Pattern matching in message text
  if (
    text.includes('[✕ BLOCK') ||
    text.includes('[BLOCK') ||
    text.includes('🛑') ||
    text.includes('Action blocked:') ||
    text.includes('Action Blocked') ||
    text.includes('blocked by policy') ||
    text.includes('Blocked by') ||
    text.includes('Gateway Reason: Command matched forbidden') ||
    text.includes('Gateway Reason: Path traversal')
  ) {
    const ruleMatch = text.match(/\[(?:✕\s*)?BLOCK\s*\|\s*([A-Z0-9_-]+)\]/) || text.match(/\(([A-Z0-9_-]+)\)/);
    return {
      decision: 'block',
      ruleId: ruleMatch ? ruleMatch[1] : (latestLog?.decision === 'block' ? latestLog.rule_id : 'POLICY-BLOCK'),
      reason: latestLog?.decision === 'block' ? latestLog.reason : 'Execution denied by Host Security Gateway',
    };
  }

  if (
    text.includes('[? ASK') ||
    text.includes('[ASK') ||
    text.includes('Pending Approval') ||
    text.includes('ACTION REQUIRED') ||
    text.includes('requires approval') ||
    text.includes('escalating to HITL')
  ) {
    const ruleMatch = text.match(/\[(?:\?\s*)?ASK\s*\|\s*([A-Z0-9_-]+)\]/) || text.match(/\(([A-Z0-9_-]+)\)/);
    return {
      decision: 'ask',
      ruleId: ruleMatch ? ruleMatch[1] : (latestLog?.decision === 'ask' ? latestLog.rule_id : 'CMD-ASK'),
      reason: latestLog?.decision === 'ask' ? latestLog.reason : 'Escalated to Human-in-the-Loop operator approval',
    };
  }

  if (
    text.includes('[✓ ALLOW') ||
    text.includes('[ALLOW') ||
    (text.includes('Tool Call:') && text.includes('Result:')) ||
    text.includes('Successfully wrote') ||
    text.includes('Action permitted')
  ) {
    const ruleMatch = text.match(/\[(?:✓\s*)?ALLOW\s*\|\s*([A-Z0-9_-]+)\]/) || text.match(/\(([A-Z0-9_-]+)\)/);
    return {
      decision: 'allow',
      ruleId: ruleMatch ? ruleMatch[1] : (latestLog?.decision === 'allow' ? latestLog.rule_id : 'POL-PASS'),
      reason: latestLog?.decision === 'allow' ? latestLog.reason : 'Action approved under active workspace security policy',
    };
  }

  // 3. If this is the most recent agent answer in the stream, link with latest gateway audit log
  if (isLastAgentMsg && latestLog) {
    return {
      decision: latestLog.decision,
      ruleId: latestLog.rule_id,
      reason: latestLog.reason,
    };
  }

  return { decision: null };
};

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
  const auditLogs = useLiveStore((s) => s.auditLogs);
  const latestLog = auditLogs[0];
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

          {latestLog && (
            <span
              className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase flex items-center gap-1 shadow-xs ${
                latestLog.decision === 'block'
                  ? 'bg-block text-white border-block'
                  : latestLog.decision === 'ask'
                  ? 'bg-ask text-white border-ask'
                  : 'bg-allow text-white border-allow'
              }`}
              title={`Last Policy Gate Decision: ${latestLog.decision.toUpperCase()} (${latestLog.rule_id})`}
            >
              {latestLog.decision === 'block' ? '✕ BLOCK' : latestLog.decision === 'ask' ? '? ASK' : '✓ ALLOWED'}
            </span>
          )}

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
            const lastAgentIdx = agentMessages.map((m) => m.role).lastIndexOf('agent');
            const isLastAgentMsg = idx === lastAgentIdx;
            const verdict = isAgent ? getMessageVerdict(msg, isLastAgentMsg, latestLog) : { decision: null };
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

                  {/* Policy Decision Verdict Banner directly after answer */}
                  {isAgent && verdict.decision && (
                    <div
                      className={`mt-2.5 pt-2 border-t flex flex-col gap-1.5 transition-all rounded-lg p-2.5 ${
                        verdict.decision === 'block'
                          ? 'bg-block/10 border-block/40 text-block'
                          : verdict.decision === 'ask'
                          ? 'bg-ask/10 border-ask/40 text-ask'
                          : 'bg-allow/10 border-allow/40 text-allow'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-1.5 font-bold text-xs uppercase tracking-wide">
                          {verdict.decision === 'block' && (
                            <span className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-block text-white font-extrabold shadow-xs text-[10px] tracking-wider">
                              <XCircle className="w-3.5 h-3.5 shrink-0" />
                              <span>BLOCK</span>
                            </span>
                          )}
                          {verdict.decision === 'ask' && (
                            <span className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-ask text-white font-extrabold shadow-xs animate-pulse text-[10px] tracking-wider">
                              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                              <span>ASK</span>
                            </span>
                          )}
                          {verdict.decision === 'allow' && (
                            <span className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-allow text-white font-extrabold shadow-xs text-[10px] tracking-wider">
                              <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                              <span>ALLOWED</span>
                            </span>
                          )}
                          <span className="text-[11px] font-semibold text-ink">
                            {verdict.decision === 'block'
                              ? 'Execution Denied by Policy'
                              : verdict.decision === 'ask'
                              ? 'Operator Approval Required'
                              : 'Execution Permitted'}
                          </span>
                        </div>

                        {verdict.ruleId && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded font-semibold bg-surface border border-line text-muted">
                            Rule: <strong className="text-ink">{verdict.ruleId}</strong>
                          </span>
                        )}
                      </div>

                      {verdict.reason && (
                        <div className="text-[11px] leading-snug font-sans text-ink/80 bg-surface/80 p-2 rounded border border-line/50 mt-0.5">
                          <span className="font-semibold text-muted">Gateway Verdict: </span>
                          <span>{verdict.reason}</span>
                        </div>
                      )}
                    </div>
                  )}
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
