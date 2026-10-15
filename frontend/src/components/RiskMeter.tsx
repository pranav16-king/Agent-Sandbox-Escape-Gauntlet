import React from 'react';

interface RiskMeterProps {
  score: number | null;
  showLabel?: boolean;
  className?: string;
}

export const RiskMeter: React.FC<RiskMeterProps> = ({
  score,
  showLabel = true,
  className = '',
}) => {
  if (score === null || score === undefined) {
    return <span className="text-muted text-xs font-mono">—</span>;
  }

  const normalized = Math.max(0, Math.min(1, score));
  const pct = Math.round(normalized * 100);

  let barColor = 'bg-allow';
  let textColor = 'text-allow';
  if (normalized >= 0.75) {
    barColor = 'bg-block';
    textColor = 'text-block';
  } else if (normalized >= 0.40) {
    barColor = 'bg-ask';
    textColor = 'text-ask';
  }

  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      <div
        className="w-16 h-2 rounded-full bg-raised overflow-hidden border border-line"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Risk score: ${pct}%`}
      >
        <div
          className={`h-full transition-all duration-300 rounded-full ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <span className={`text-xs font-mono font-medium ${textColor}`}>
          {normalized.toFixed(2)}
        </span>
      )}
    </div>
  );
};
