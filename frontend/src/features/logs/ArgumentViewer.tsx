import React, { useState, useMemo } from 'react';
import { Terminal, FileText, Globe, ShieldAlert, Copy, Check, Code, Eye, FileCode, CheckCircle2 } from 'lucide-react';
import { JsonView, deepDecodeJson } from '@/components/JsonView';

interface ArgumentViewerProps {
  rawArgs: string;
  tool?: string;
  className?: string;
}

export const ArgumentViewer: React.FC<ArgumentViewerProps> = ({
  rawArgs,
  tool = '',
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState<'human' | 'json' | 'raw'>('human');
  const [copied, setCopied] = useState(false);

  // Safely decode and parse JSON arguments
  const { parsedArgs, isJson, isUrlEncoded, decodedString } = useMemo(() => {
    let parsed: any = null;
    let isJ = false;
    let isUrl = false;
    let decoded = rawArgs || '';

    if (!rawArgs) {
      return { parsedArgs: null, isJson: false, isUrlEncoded: false, decodedString: '' };
    }

    // Check URL-encoding
    if (typeof rawArgs === 'string' && (rawArgs.includes('%20') || rawArgs.includes('%2F') || rawArgs.includes('%3A') || rawArgs.includes('%26'))) {
      try {
        const attempt = decodeURIComponent(rawArgs);
        if (attempt !== rawArgs) {
          isUrl = true;
          decoded = attempt;
        }
      } catch {}
    }

    // Try parsing as JSON
    try {
      parsed = JSON.parse(decoded);
      isJ = true;
      // Handle double-encoded JSON strings
      if (typeof parsed === 'string') {
        try {
          parsed = JSON.parse(parsed);
        } catch {}
      }
    } catch {
      // Not JSON, check if raw string was JSON without URL decode
      try {
        parsed = JSON.parse(rawArgs);
        isJ = true;
      } catch {
        parsed = null;
      }
    }

    return {
      parsedArgs: parsed ? deepDecodeJson(parsed) : null,
      isJson: isJ,
      isUrlEncoded: isUrl,
      decodedString: decoded,
    };
  }, [rawArgs]);

  const handleCopy = (textToCopy: string) => {
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  // Render Human-Readable Breakdown
  const renderHumanReadable = () => {
    if (!rawArgs || rawArgs === '<empty>' || rawArgs === '{}') {
      return <div className="text-muted italic text-xs p-3">No arguments provided.</div>;
    }

    if (!isJson || !parsedArgs || typeof parsedArgs !== 'object') {
      return (
        <div className="p-3 rounded-lg border border-line bg-raised/40 space-y-2">
          {isUrlEncoded && (
            <div className="flex items-center gap-1.5 text-[10px] font-mono text-accent">
              <CheckCircle2 className="w-3 h-3" />
              <span>URL-decoded content:</span>
            </div>
          )}
          <div className="font-mono text-xs text-ink break-all whitespace-pre-wrap select-all">
            {decodedString}
          </div>
        </div>
      );
    }

    // Specialized renderers based on tool or arguments
    const toolLower = tool.toLowerCase();

    // 1. Shell Command
    if (toolLower === 'shell' || parsedArgs.cmd) {
      const command = parsedArgs.cmd || parsedArgs.command || '';
      return (
        <div className="space-y-2.5">
          <div className="rounded-lg border border-line bg-raised/70 p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-muted uppercase flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-accent" />
                Shell Executable
              </span>
              <button
                type="button"
                onClick={() => handleCopy(command)}
                className="px-2 py-0.5 rounded text-[10px] font-mono border border-line bg-surface hover:bg-raised text-muted hover:text-ink transition-colors flex items-center gap-1"
              >
                {copied ? <Check className="w-3 h-3 text-allow" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <div className="font-mono text-xs bg-bg/80 border border-line/60 rounded-md p-2.5 text-accent select-all break-all flex items-start gap-2">
              <span className="text-muted select-none">$</span>
              <span>{command || '<empty>'}</span>
            </div>
            {parsedArgs.timeout && (
              <div className="text-[10px] font-mono text-muted flex items-center justify-between pt-1 border-t border-line/40">
                <span>Timeout Budget:</span>
                <span className="text-ink font-semibold">{parsedArgs.timeout}s</span>
              </div>
            )}
          </div>
        </div>
      );
    }

    // 2. File Operations
    if (toolLower === 'file' || parsedArgs.op || parsedArgs.path) {
      const op = String(parsedArgs.op || 'read').toUpperCase();
      const path = parsedArgs.path || '<unspecified>';
      const content = parsedArgs.content;
      const opColor = op === 'WRITE' ? 'text-ask bg-ask-bg border-ask/40' : op === 'LIST' ? 'text-accent bg-accent/20 border-accent/40' : 'text-allow bg-allow-bg border-allow/40';

      return (
        <div className="space-y-2.5">
          <div className="rounded-lg border border-line bg-raised/70 p-3 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-muted uppercase flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-accent" />
                File Action
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border uppercase ${opColor}`}>
                {op}
              </span>
            </div>

            <div>
              <span className="text-[10px] text-muted block mb-1">Target Workspace Path:</span>
              <div className="font-mono text-xs bg-bg/80 border border-line/60 rounded-md p-2 text-ink break-all flex items-center justify-between gap-2">
                <span className="select-all">{path}</span>
                <button
                  type="button"
                  onClick={() => handleCopy(path)}
                  className="shrink-0 text-muted hover:text-ink p-1 rounded hover:bg-raised transition-colors"
                  title="Copy path"
                >
                  <Copy className="w-3 h-3" />
                </button>
              </div>
            </div>

            {content !== undefined && content !== null && (
              <div>
                <span className="text-[10px] text-muted block mb-1">
                  File Payload ({String(content).length} bytes):
                </span>
                <div className="font-mono text-xs bg-bg/80 border border-line/60 rounded-md p-2.5 max-h-36 overflow-y-auto whitespace-pre-wrap break-all text-ink">
                  {String(content)}
                </div>
              </div>
            )}
          </div>
        </div>
      );
    }

    // 3. HTTP / Network Operations
    if (toolLower === 'http' || parsedArgs.url) {
      const method = String(parsedArgs.method || 'GET').toUpperCase();
      const url = parsedArgs.url || '<unspecified>';
      const body = parsedArgs.body;

      return (
        <div className="space-y-2.5">
          <div className="rounded-lg border border-line bg-raised/70 p-3 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-muted uppercase flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-accent" />
                Network Target
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-accent/20 border border-accent/40 text-accent uppercase">
                {method}
              </span>
            </div>

            <div>
              <span className="text-[10px] text-muted block mb-1">Destination URL:</span>
              <div className="font-mono text-xs bg-bg/80 border border-line/60 rounded-md p-2 text-ink break-all flex items-center justify-between gap-2">
                <span className="select-all">{url}</span>
                <button
                  type="button"
                  onClick={() => handleCopy(url)}
                  className="shrink-0 text-muted hover:text-ink p-1 rounded hover:bg-raised transition-colors"
                  title="Copy URL"
                >
                  <Copy className="w-3 h-3" />
                </button>
              </div>
            </div>

            {body && (
              <div>
                <span className="text-[10px] text-muted block mb-1">Request Body:</span>
                <div className="font-mono text-xs bg-bg/80 border border-line/60 rounded-md p-2.5 max-h-32 overflow-y-auto whitespace-pre-wrap break-all text-ink">
                  {typeof body === 'object' ? JSON.stringify(body, null, 2) : String(body)}
                </div>
              </div>
            )}
          </div>
        </div>
      );
    }

    // 4. Prompt Guard / Injection Review
    if (parsedArgs.prompt_preview || parsedArgs.risk_score !== undefined) {
      return (
        <div className="space-y-2.5">
          <div className="rounded-lg border border-line bg-raised/70 p-3 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-muted uppercase flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5 text-block" />
                Prompt Evaluation Arguments
              </span>
              {parsedArgs.risk_score !== undefined && (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-block-bg border border-block/40 text-block">
                  Risk: {(Number(parsedArgs.risk_score) * 100).toFixed(0)}%
                </span>
              )}
            </div>

            {parsedArgs.prompt_preview && (
              <div>
                <span className="text-[10px] text-muted block mb-1">Prompt Sample:</span>
                <div className="font-mono text-xs bg-bg/80 border border-line/60 rounded-md p-2.5 text-ink whitespace-pre-wrap break-all">
                  "{parsedArgs.prompt_preview}"
                </div>
              </div>
            )}
          </div>
        </div>
      );
    }

    // 5. Generic Key-Value Breakdown for arbitrary structured arguments
    return (
      <div className="rounded-lg border border-line bg-raised/50 divide-y divide-line/60 text-xs font-mono">
        {Object.entries(parsedArgs).map(([key, value]) => (
          <div key={key} className="p-2.5 flex flex-col sm:flex-row sm:items-start justify-between gap-2">
            <span className="text-muted font-semibold min-w-[120px] text-[11px] uppercase tracking-wider">
              {key}:
            </span>
            <span className="text-ink break-all text-left flex-1 font-mono">
              {typeof value === 'object' && value !== null
                ? JSON.stringify(value)
                : String(value)}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Subheader Toolbar with View Mode Tabs */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-1.5">
          <FileCode className="w-3.5 h-3.5 text-accent" />
          Command &amp; Payload Inspector
        </span>

        <div className="flex items-center gap-1 bg-raised/70 p-0.5 rounded-lg border border-line/60">
          <button
            type="button"
            onClick={() => setActiveTab('human')}
            className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors flex items-center gap-1 ${
              activeTab === 'human'
                ? 'bg-accent text-on-accent font-bold shadow-xs'
                : 'text-muted hover:text-ink'
            }`}
            title="Human-readable structured view"
          >
            <Eye className="w-3 h-3" />
            <span>Readable</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('json')}
            className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors flex items-center gap-1 ${
              activeTab === 'json'
                ? 'bg-accent text-on-accent font-bold shadow-xs'
                : 'text-muted hover:text-ink'
            }`}
            title="Pretty-printed JSON view"
          >
            <Code className="w-3 h-3" />
            <span>Decoded JSON</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('raw')}
            className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
              activeTab === 'raw'
                ? 'bg-accent text-on-accent font-bold shadow-xs'
                : 'text-muted hover:text-ink'
            }`}
            title="Exact wire string"
          >
            Raw
          </button>
        </div>
      </div>

      {/* Content Panes */}
      {activeTab === 'human' && renderHumanReadable()}

      {activeTab === 'json' && (
        <JsonView
          data={parsedArgs || { raw: rawArgs }}
          maxHeight="max-h-56"
          showModeToggle={false}
        />
      )}

      {activeTab === 'raw' && (
        <div className="relative rounded-lg border border-line bg-raised p-3 text-xs font-mono break-all text-ink selection:bg-accent selection:text-on-accent max-h-56 overflow-y-auto whitespace-pre-wrap">
          <button
            type="button"
            onClick={() => handleCopy(rawArgs)}
            className="absolute right-2 top-2 p-1 rounded bg-surface/80 hover:bg-surface border border-line text-muted hover:text-ink transition-colors"
            title="Copy raw string"
          >
            {copied ? <Check className="w-3 h-3 text-allow" /> : <Copy className="w-3 h-3" />}
          </button>
          {rawArgs || '<empty>'}
        </div>
      )}
    </div>
  );
};
