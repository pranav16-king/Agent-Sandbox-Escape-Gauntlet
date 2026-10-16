import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'secondary',
  size = 'md',
  icon,
  children,
  className = '',
  disabled,
  ...props
}) => {
  const base = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent select-none disabled:opacity-50 disabled:cursor-not-allowed';

  const sizeStyles = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    md: 'text-xs px-3.5 py-2 gap-2 min-h-[36px]',
    lg: 'text-sm px-4 py-2.5 gap-2.5 min-h-[40px]',
  }[size];

  const variantStyles = {
    primary: 'bg-accent text-on-accent hover:opacity-90 active:scale-[0.98]',
    secondary: 'bg-raised hover:bg-surface text-ink border border-line',
    outline: 'border border-line hover:bg-raised text-ink bg-transparent',
    danger: 'bg-block-bg text-block border border-block/30 hover:bg-block/20',
    ghost: 'hover:bg-raised text-muted hover:text-ink',
  }[variant];

  return (
    <button
      className={`${base} ${sizeStyles} ${variantStyles} ${className}`}
      disabled={disabled}
      {...props}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </button>
  );
};
