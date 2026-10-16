import React from 'react';

export const Skeleton: React.FC<{ className?: string }> = ({ className = '' }) => {
  return (
    <div
      className={`animate-pulse rounded bg-raised/70 ${className}`}
      aria-hidden="true"
    />
  );
};
