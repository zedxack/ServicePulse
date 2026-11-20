import React from 'react';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'rect' | 'circle' | 'card' | 'table';
  count?: number;
  height?: string;
  width?: string;
}

export const LoadingSkeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'rect',
  count = 1,
  height,
  width,
}) => {
  const sizeClasses = `${height || ''} ${width || ''}`.trim();
  const baseClasses = `motion-safe:animate-pulse bg-surface-200 dark:bg-surface-800 rounded-md ${sizeClasses}`;

  if (variant === 'circle') {
    return <div className={`rounded-full ${baseClasses} ${className}`} />;
  }

  if (variant === 'card') {
    return (
      <div
        className={`rounded-xl border border-surface-200 bg-white p-5 shadow-xs dark:border-white/10 dark:bg-surface-900 ${sizeClasses} ${className}`}
      >
        <div className={`h-3 w-1/3 motion-safe:animate-pulse bg-surface-200 dark:bg-surface-800 rounded-md`} />
        <div className={`mt-3 h-8 w-1/2 motion-safe:animate-pulse bg-surface-200 dark:bg-surface-800 rounded-md`} />
        <div className={`mt-3 h-3 w-3/4 motion-safe:animate-pulse bg-surface-200 dark:bg-surface-800 rounded-md`} />
      </div>
    );
  }

  if (variant === 'table') {
    return (
      <div className={`space-y-3 p-4 ${sizeClasses} ${className}`}>
        <div className={`h-4 w-full motion-safe:animate-pulse bg-surface-200 dark:bg-surface-800 rounded-md`} />
        <div className={`h-8 w-full motion-safe:animate-pulse bg-surface-200 dark:bg-surface-800 rounded-md`} />
        <div className={`h-8 w-full motion-safe:animate-pulse bg-surface-200 dark:bg-surface-800 rounded-md`} />
        <div className={`h-8 w-full motion-safe:animate-pulse bg-surface-200 dark:bg-surface-800 rounded-md`} />
      </div>
    );
  }

  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={`${baseClasses} ${className}`} />
      ))}
    </>
  );
};
