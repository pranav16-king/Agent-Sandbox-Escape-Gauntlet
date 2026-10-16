import React from 'react';
import { Check, X, HelpCircle } from 'lucide-react';
import { Decision } from '@/api/types';

interface DecisionBadgeProps {
  decision: Decision;
  size?: 'sm' | 'md';
  className?: string;
}

export const DecisionBadge: React.FC<DecisionBadgeProps> = ({
  decision,
  size = 'md',
  className = '',
}) => {
  const configs = {
    allow: {
      label: 'ALLOW',
      icon: <Check className={size === 'sm' ? 'w-3 h-3 stroke-[2.5]' : 'w-3.5 h-3.5 stroke-[2.5]'} />,
      classes: 'text-allow bg-allow-bg border-allow/30',
    },
    block: {
      label: 'BLOCK',
      icon: <X className={size === 'sm' ? 'w-3 h-3 stroke-[2.5]' : 'w-3.5 h-3.5 stroke-[2.5]'} />,
      classes: 'text-block bg-block-bg border-block/30',
    },
    ask: {
      label: 'ASK',
      icon: <HelpCircle className={size === 'sm' ? 'w-3 h-3 stroke-[2.5]' : 'w-3.5 h-3.5 stroke-[2.5]'} />,
      classes: 'text-ask bg-ask-bg border-ask/30',
    },
  }[decision] || {
    label: decision.toUpperCase(),
    icon: null,
    classes: 'text-muted bg-raised border-line',
  };

  const sizeClasses = size === 'sm'
    ? 'text-[11px] px-1.5 py-0.5 gap-1'
    : 'text-xs px-2.5 py-1 gap-1.5';

  return (
    <span
      className={`inline-flex items-center font-mono font-semibold rounded-md border tracking-wider select-none ${sizeClasses} ${configs.classes} ${className}`}
      role="status"
      aria-label={`Decision: ${configs.label}`}
    >
      <span className="shrink-0">{configs.icon}</span>
      <span>{configs.label}</span>
    </span>
  );
};
