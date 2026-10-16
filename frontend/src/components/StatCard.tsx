import React, { useEffect, useState, useRef } from 'react';

interface StatCardProps {
  label: string;
  value: number;
  total?: number;
  subtitle?: string;
  icon?: React.ReactNode;
  variant?: 'default' | 'allow' | 'block' | 'ask' | 'accent';
  flashOnIncrement?: boolean;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  total,
  subtitle,
  icon,
  variant = 'default',
  flashOnIncrement = false,
}) => {
  const [displayValue, setDisplayValue] = useState(value);
  const [flashing, setFlashing] = useState(false);
  const prevValueRef = useRef(value);

  // Animated count-up
  useEffect(() => {
    const prev = prevValueRef.current;
    if (prev !== value) {
      if (flashOnIncrement && value > prev) {
        setFlashing(true);
        const timer = setTimeout(() => setFlashing(false), 800);
        return () => clearTimeout(timer);
      }

      // Check reduced motion preference
      const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (prefersReducedMotion) {
        setDisplayValue(value);
      } else {
        const start = prev;
        const diff = value - start;
        const duration = 400;
        const startTime = performance.now();

        const animate = (currentTime: number) => {
          const elapsed = currentTime - startTime;
          const progress = Math.min(elapsed / duration, 1);
          // Ease-out
          const currentVal = Math.round(start + diff * (1 - Math.pow(1 - progress, 3)));
          setDisplayValue(currentVal);

          if (progress < 1) {
            requestAnimationFrame(animate);
          } else {
            setDisplayValue(value);
          }
        };

        requestAnimationFrame(animate);
      }
      prevValueRef.current = value;
    }
  }, [value, flashOnIncrement]);

  const variantStyles = {
    default: 'text-ink',
    allow: 'text-allow',
    block: 'text-block',
    ask: 'text-ask',
    accent: 'text-accent',
  }[variant];

  const variantBorder = {
    default: 'border-t-line',
    allow: 'border-t-allow',
    block: 'border-t-block',
    ask: 'border-t-ask',
    accent: 'border-t-accent',
  }[variant];

  // Calculate percentage if total provided
  const pct = total && total > 0 ? Math.round((value / total) * 100) : null;

  return (
    <div
      className={`relative h-[88px] rounded-card border border-line ${variantBorder} border-t-2 bg-surface p-3.5 flex flex-col justify-between card-hover ${
        flashing ? 'animate-block-flash border-block' : ''
      }`}
    >
      <div className="flex items-center justify-between text-xs text-muted font-medium">
        <span className="truncate tracking-tight">{label}</span>
        {icon && <span className="shrink-0">{icon}</span>}
      </div>

      <div className="flex items-baseline justify-between gap-2 mt-1">
        <span className={`text-[28px] font-bold font-mono leading-none tracking-tight ${variantStyles}`}>
          {displayValue.toLocaleString()}
        </span>
        {pct !== null ? (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-raised border border-line/60 text-muted">
            {pct}%
          </span>
        ) : subtitle ? (
          <span className="text-[11px] font-mono text-muted truncate">
            {subtitle}
          </span>
        ) : null}
      </div>
    </div>
  );
};
