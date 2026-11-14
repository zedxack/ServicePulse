import React from 'react';
import { Loader2 } from 'lucide-react';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success';
export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  disabled,
  className = '',
  ...props
}) => {
  const sizeClasses: Record<ButtonSize, string> = {
    xs: 'px-2.5 py-1 text-xs gap-1.5 rounded',
    sm: 'px-3 py-1.5 text-xs gap-1.5 rounded-lg font-medium',
    md: 'px-4 py-2 text-xs gap-2 rounded-lg font-semibold',
    lg: 'px-5 py-2.5 text-sm gap-2.5 rounded-xl font-semibold',
  };

  const variantClasses: Record<ButtonVariant, string> = {
    primary:
      'bg-brand-600 text-white shadow-xs hover:bg-brand-500 active:bg-brand-700 dark:bg-brand-600 dark:hover:bg-brand-500 focus-visible:ring-2 focus-visible:ring-brand-500/50',
    secondary:
      'bg-surface-100 text-surface-800 hover:bg-surface-200 active:bg-surface-300 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700 focus-visible:ring-2 focus-visible:ring-surface-400/50',
    outline:
      'border border-surface-300 bg-transparent text-surface-700 hover:bg-surface-50 dark:border-white/10 dark:text-surface-300 dark:hover:bg-surface-800/60 focus-visible:ring-2 focus-visible:ring-brand-500/50',
    ghost:
      'bg-transparent text-surface-600 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-800 dark:hover:text-white',
    danger:
      'bg-red-600 text-white shadow-xs hover:bg-red-500 active:bg-red-700 dark:bg-red-600 dark:hover:bg-red-500 focus-visible:ring-2 focus-visible:ring-red-500/50',
    success:
      'bg-emerald-600 text-white shadow-xs hover:bg-emerald-500 active:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-500 focus-visible:ring-2 focus-visible:ring-emerald-500/50',
  };

  return (
    <button
      disabled={disabled || isLoading}
      className={`inline-flex items-center justify-center transition-all duration-150 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        leftIcon
      )}
      <span>{children}</span>
      {!isLoading && rightIcon}
    </button>
  );
};
