import React, { useState, useMemo } from 'react';
import { Copy, Check, Code2, Layers } from 'lucide-react';

interface JsonViewProps {
  data: unknown;
  className?: string;
  maxHeight?: string;
  showModeToggle?: boolean;
}

// Deeply unwraps stringified JSON and URL-encoded objects
export function deepDecodeJson(value: any): any {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (
      (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))
    ) {
      try {
        const parsed = JSON.parse(trimmed);
        return deepDecodeJson(parsed);
      } catch {}
    }
    // Check if URL-encoded JSON
    if (trimmed.includes('%7B') || trimmed.includes('%22') || trimmed.includes('%5B')) {
      try {
        const urlDecoded = decodeURIComponent(trimmed);
        if (
          (urlDecoded.startsWith('{') && urlDecoded.endsWith('}')) ||
          (urlDecoded.startsWith('[') && urlDecoded.endsWith(']'))
        ) {
          return deepDecodeJson(JSON.parse(urlDecoded));
        }
      } catch {}
    }
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(deepDecodeJson);
  }
  if (value && typeof value === 'object') {
    const out: Record<string, any> = {};
    for (const [k, v] of Object.entries(value)) {
      out[k] = deepDecodeJson(v);
    }
    return out;
  }
  return value;
}

// Tokenize and syntax-highlight JSON lines
function renderSyntaxHighlightedJson(jsonText: string): React.ReactNode[] {
  const lines = jsonText.split('\n');

  return lines.map((line, lineIdx) => {
    const parts: React.ReactNode[] = [];
    // Tokenizer regex matching JSON keys, strings, booleans, nulls, numbers, and brackets
    const tokenRegex = /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(?:true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?|[{}[\],:])/g;

    let lastIdx = 0;
    let match: RegExpExecArray | null;

    while ((match = tokenRegex.exec(line)) !== null) {
      const start = match.index;
      if (start > lastIdx) {
        parts.push(line.substring(lastIdx, start));
      }

      const token = match[0];
      const isKey = token.startsWith('"') && token.endsWith(':');
      const isString = token.startsWith('"') && !isKey;
      const isBoolean = token === 'true' || token === 'false';
      const isNull = token === 'null';
      const isNumber = /^-?\d/.test(token);
      const isPunctuation = /^[{}[\],:]$/.test(token);

      let color = 'text-ink';
      if (isKey) color = 'text-accent font-semibold';
      else if (isString) color = 'text-allow';
      else if (isNumber) color = 'text-ask font-semibold';
      else if (isBoolean) color = 'text-block font-bold';
      else if (isNull) color = 'text-muted italic';
      else if (isPunctuation) color = 'text-muted/70';

      parts.push(
        <span key={`${lineIdx}-${match.index}`} className={color}>
          {token}
        </span>
      );
      lastIdx = tokenRegex.lastIndex;
    }

    if (lastIdx < line.length) {
      parts.push(line.substring(lastIdx));
    }

    return (
      <div key={lineIdx} className="leading-5">
        {parts.length > 0 ? parts : ' '}
      </div>
    );
  });
}

export const JsonView: React.FC<JsonViewProps> = ({
  data,
  className = '',
  maxHeight = 'max-h-60',
  showModeToggle = true,
}) => {
  const [copied, setCopied] = useState(false);
  const [mode, setMode] = useState<'decoded' | 'raw'>('decoded');

  const { decodedText, rawText, hasDifference } = useMemo(() => {
    let r = '';
    let d = '';

    try {
      r = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    } catch {
      r = String(data);
    }

    try {
      const decodedObj = deepDecodeJson(data);
      d = JSON.stringify(decodedObj, null, 2);
    } catch {
      d = r;
    }

    return {
      decodedText: d,
      rawText: r,
      hasDifference: d !== r && typeof data === 'object' && data !== null,
    };
  }, [data]);

  const activeText = mode === 'decoded' ? decodedText : rawText;

  const handleCopy = () => {
    navigator.clipboard.writeText(activeText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className={`relative rounded-lg border border-line bg-surface/90 overflow-hidden ${className}`}>
      {/* Top Bar with Mode Toggle and Copy Button */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-line bg-raised/50 text-[11px] font-mono">
        <div className="flex items-center gap-1.5 text-muted">
          <Code2 className="w-3.5 h-3.5 text-accent" />
          <span>JSON Viewer</span>
        </div>

        <div className="flex items-center gap-2">
          {showModeToggle && hasDifference && (
            <div className="flex items-center gap-1 bg-surface p-0.5 rounded border border-line/60">
              <button
                type="button"
                onClick={() => setMode('decoded')}
                className={`px-1.5 py-0.5 rounded text-[10px] transition-colors flex items-center gap-1 ${
                  mode === 'decoded'
                    ? 'bg-accent text-on-accent font-bold'
                    : 'text-muted hover:text-ink'
                }`}
                title="Unescapes nested JSON strings into clean native objects"
              >
                <Layers className="w-3 h-3" />
                <span>Decoded</span>
              </button>
              <button
                type="button"
                onClick={() => setMode('raw')}
                className={`px-1.5 py-0.5 rounded text-[10px] transition-colors ${
                  mode === 'raw'
                    ? 'bg-accent text-on-accent font-bold'
                    : 'text-muted hover:text-ink'
                }`}
                title="Exact wire format as received"
              >
                Raw Wire
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={handleCopy}
            className="p-1 rounded bg-raised hover:bg-surface border border-line text-muted hover:text-ink transition-colors flex items-center gap-1"
            title="Copy JSON"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-allow" />
                <span className="text-[10px] text-allow font-semibold">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span className="text-[10px]">Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Syntax-highlighted body */}
      <div className={`p-3 font-mono text-xs overflow-auto select-text selection:bg-accent selection:text-on-accent ${maxHeight}`}>
        {renderSyntaxHighlightedJson(activeText)}
      </div>
    </div>
  );
};
