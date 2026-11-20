import React from 'react';

export type BadgeVariant =
  | 'default'
  | 'online'
  | 'offline'
  | 'warning'
  | 'info'
  | 'brand'
  | 'purple'
  | 'outline'
  | 'mono';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'xs' | 'sm' | 'md';
  dot?: boolean;
  mono?: boolean;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'sm',
  dot = false,
  mono = false,
  className = '',
}) => {
  const sizeClasses = {
    xs: 'px-1.5 py-0.5 text-[10px]',
    sm: 'px-2 py-0.5 text-[11px]',
    md: 'px-2.5 py-1 text-xs',
  };

  const variantClasses: Record<BadgeVariant, { bg: string; dot?: string }> = {
    default: {
      bg: 'bg-surface-100 text-surface-700 border-surface-200 dark:bg-surface-800 dark:text-surface-300 dark:border-white/10',
      dot: 'bg-surface-400',
    },
    online: {
      bg: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/40',
      dot: 'bg-emerald-500',
    },
    offline: {
      bg: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-800/40',
      dot: 'bg-red-500',
    },
    warning: {
      bg: 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/40',
      dot: 'bg-amber-500',
    },
    info: {
      bg: 'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/40 dark:text-sky-300 dark:border-sky-800/40',
      dot: 'bg-sky-500',
    },
    brand: {
      bg: 'bg-brand-50 text-brand-700 border-brand-200 dark:bg-brand-950/40 dark:text-brand-300 dark:border-brand-800/40',
      dot: 'bg-brand-500',
    },
    purple: {
      bg: 'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800/40',
      dot: 'bg-purple-500',
    },
    outline: {
      bg: 'bg-transparent text-surface-700 border-surface-300 dark:text-surface-300 dark:border-white/20',
    },
    mono: {
      bg: 'bg-surface-100 text-surface-700 border-surface-200 dark:bg-surface-800 dark:text-surface-300 dark:border-white/10 font-mono',
      dot: 'bg-surface-400',
    },
  };

  const style = variantClasses[variant] || variantClasses.default;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${
        style.bg
      } ${sizeClasses[size]} ${mono ? 'font-mono' : ''} ${className}`}
    >
      {dot && style.dot && (
        <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      )}
      {children}
    </span>
  );
};
