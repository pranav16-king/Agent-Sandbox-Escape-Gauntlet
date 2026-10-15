import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface HashChipProps {
  hash: string;
  truncateLength?: number;
  className?: string;
}

export const HashChip: React.FC<HashChipProps> = ({
  hash,
  truncateLength = 8,
  className = '',
}) => {
  const [copied, setCopied] = useState(false);

  if (!hash) {
    return <span className="text-muted text-xs font-mono">None</span>;
  }

  const truncated =
    hash.length > truncateLength * 2
      ? `${hash.slice(0, truncateLength)}…${hash.slice(-truncateLength)}`
      : hash;

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={`Click to copy: ${hash}`}
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded font-mono text-[11px] bg-raised hover:bg-raised/80 text-muted hover:text-ink border border-line transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent ${className}`}
    >
      <span>{truncated}</span>
      {copied ? (
        <Check className="w-3 h-3 text-allow shrink-0" />
      ) : (
        <Copy className="w-3 h-3 text-muted shrink-0 opacity-70 hover:opacity-100" />
      )}
    </button>
  );
};
