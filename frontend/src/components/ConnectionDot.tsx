import React from 'react';
import { RefreshCw } from 'lucide-react';

interface ConnectionDotProps {
  status: 'connected' | 'reconnecting' | 'offline';
  retryCount?: number;
  className?: string;
  onReconnect?: () => void;
}

export const ConnectionDot: React.FC<ConnectionDotProps> = ({
  status,
  retryCount = 0,
  className = '',
  onReconnect,
}) => {
  const configs = {
    connected: {
      color: 'bg-allow',
      ping: 'bg-allow/40',
      label: 'LIVE',
      textClass: 'text-allow',
    },
    reconnecting: {
      color: 'bg-ask',
      ping: 'bg-ask/40',
      label: retryCount > 0 ? `RECONNECTING (${retryCount})` : 'RECONNECTING',
      textClass: 'text-ask',
    },
    offline: {
      color: 'bg-block',
      ping: 'transparent',
      label: 'OFFLINE',
      textClass: 'text-block',
    },
  }[status];

  const isClickable = status !== 'connected' && Boolean(onReconnect);

  return (
    <button
      type="button"
      onClick={onReconnect}
      disabled={status === 'connected'}
      title={
        status === 'offline'
          ? 'Gateway Offline — Click to reconnect now'
          : status === 'reconnecting'
          ? 'Reconnecting to Gateway — Click to force retry'
          : 'Gateway Connected & Synchronized (LIVE)'
      }
      className={`flex items-center gap-2 select-none px-2 py-1 rounded-md transition-colors ${
        isClickable
          ? 'cursor-pointer hover:bg-raised active:scale-95 border border-line/60'
          : 'cursor-default border border-transparent'
      } ${className}`}
    >
      <div className="relative flex items-center justify-center">
        {status !== 'offline' && (
          <span className={`absolute w-3 h-3 rounded-full animate-ping opacity-75 ${configs.ping}`} />
        )}
        <span className={`relative w-2 h-2 rounded-full ${configs.color}`} />
      </div>
      <span className={`text-[11px] font-mono font-semibold tracking-wider ${configs.textClass}`}>
        {configs.label}
      </span>
      {isClickable && (
        <RefreshCw className="w-2.5 h-2.5 text-muted animate-spin shrink-0 opacity-70" />
      )}
    </button>
  );
};
