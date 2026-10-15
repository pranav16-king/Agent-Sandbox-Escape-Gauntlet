import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface JsonViewProps {
  data: unknown;
  className?: string;
  maxHeight?: string;
}

export const JsonView: React.FC<JsonViewProps> = ({
  data,
  className = '',
  maxHeight = 'max-h-60',
}) => {
  const [copied, setCopied] = useState(false);

  let formatted = '';
  try {
    formatted = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  } catch {
    formatted = String(data);
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(formatted);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className={`relative rounded-lg border border-line bg-raised/50 ${className}`}>
      <div className="absolute right-2 top-2 z-10">
        <button
          type="button"
          onClick={handleCopy}
          className="p-1 rounded bg-surface/80 hover:bg-surface border border-line text-muted hover:text-ink transition-colors"
          title="Copy JSON"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-allow" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>

      <pre className={`p-3 font-mono text-xs overflow-auto text-ink selection:bg-accent selection:text-on-accent whitespace-pre-wrap break-all ${maxHeight}`}>
        {formatted}
      </pre>
    </div>
  );
};
