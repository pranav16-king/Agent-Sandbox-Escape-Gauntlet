import React from 'react';

interface ConnectionDotProps {
  status: 'connected' | 'reconnecting' | 'offline';
  retryCount?: number;
  className?: string;
}

export const ConnectionDot: React.FC<ConnectionDotProps> = ({
  status,
  retryCount = 0,
  className = '',
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

  return (
    <div className={`flex items-center gap-2 select-none ${className}`} title={`Connection status: ${status}`}>
      <div className="relative flex items-center justify-center">
        {status !== 'offline' && (
          <span className={`absolute w-3 h-3 rounded-full animate-ping opacity-75 ${configs.ping}`} />
        )}
        <span className={`relative w-2 h-2 rounded-full ${configs.color}`} />
      </div>
      <span className={`text-[11px] font-mono font-semibold tracking-wider ${configs.textClass}`}>
        {configs.label}
      </span>
    </div>
  );
};
