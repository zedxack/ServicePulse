import React from 'react';
import { LucideIcon } from 'lucide-react';

export type MetricAccent =
  | 'brand'
  | 'online'
  | 'warning'
  | 'critical'
  | 'purple'
  | 'neutral'
  | 'emerald'
  | 'rose'
  | 'amber'
  | 'cyan';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon | React.ReactNode;
  accent?: MetricAccent;
  accentColor?: MetricAccent | string;
  delta?: {
    value: string;
    trend: 'up' | 'down' | 'neutral';
    label?: string;
  };
  onClick?: () => void;
  className?: string;
  children?: React.ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  accent,
  accentColor,
  delta,
  onClick,
  className = '',
  children,
}) => {
  const chosenAccent = (accentColor || accent || 'brand') as MetricAccent;

  const accentStyles: Record<
    string,
    { iconBg: string; iconColor: string; barColor: string }
  > = {
    brand: {
      iconBg: 'bg-brand-50 dark:bg-brand-950/50',
      iconColor: 'text-brand-600 dark:text-brand-400',
      barColor: 'from-brand-500 to-sky-400',
    },
    online: {
      iconBg: 'bg-emerald-50 dark:bg-emerald-950/50',
      iconColor: 'text-emerald-600 dark:text-emerald-400',
      barColor: 'from-emerald-500 to-teal-400',
    },
    emerald: {
      iconBg: 'bg-emerald-50 dark:bg-emerald-950/50',
      iconColor: 'text-emerald-600 dark:text-emerald-400',
      barColor: 'from-emerald-500 to-teal-400',
    },
    warning: {
      iconBg: 'bg-amber-50 dark:bg-amber-950/50',
      iconColor: 'text-amber-600 dark:text-amber-400',
      barColor: 'from-amber-500 to-orange-400',
    },
    amber: {
      iconBg: 'bg-amber-50 dark:bg-amber-950/50',
      iconColor: 'text-amber-600 dark:text-amber-400',
      barColor: 'from-amber-500 to-orange-400',
    },
    critical: {
      iconBg: 'bg-red-50 dark:bg-red-950/50',
      iconColor: 'text-red-600 dark:text-red-400',
      barColor: 'from-red-500 to-rose-400',
    },
    rose: {
      iconBg: 'bg-red-50 dark:bg-red-950/50',
      iconColor: 'text-red-600 dark:text-red-400',
      barColor: 'from-red-500 to-rose-400',
    },
    purple: {
      iconBg: 'bg-purple-50 dark:bg-purple-950/50',
      iconColor: 'text-purple-600 dark:text-purple-400',
      barColor: 'from-purple-500 to-indigo-400',
    },
    cyan: {
      iconBg: 'bg-cyan-50 dark:bg-cyan-950/50',
      iconColor: 'text-cyan-600 dark:text-cyan-400',
      barColor: 'from-cyan-500 to-blue-400',
    },
    neutral: {
      iconBg: 'bg-surface-100 dark:bg-surface-800',
      iconColor: 'text-surface-600 dark:text-surface-300',
      barColor: 'from-surface-400 to-surface-500',
    },
    mono: {
      iconBg: 'bg-surface-100 dark:bg-surface-800',
      iconColor: 'text-surface-600 dark:text-surface-300',
      barColor: 'from-surface-400 to-surface-500',
    },
  };

  const style = accentStyles[chosenAccent] || accentStyles.brand;

  const renderIcon = () => {
    if (!icon) return null;
    if (React.isValidElement(icon)) {
      return (
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-surface-200/50 dark:border-white/5 ${style.iconBg} ${style.iconColor}`}
        >
          {icon}
        </div>
      );
    }
    const IconComp = icon as LucideIcon;
    return (
      <div
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-surface-200/50 dark:border-white/5 ${style.iconBg} ${style.iconColor}`}
      >
        <IconComp className="h-5 w-5" />
      </div>
    );
  };

  return (
    <div
      onClick={onClick}
      className={`group relative overflow-hidden rounded-xl border border-surface-200 bg-white p-5 shadow-xs transition-all duration-200 hover:border-surface-300 hover:shadow-sm dark:border-white/10 dark:bg-surface-900 dark:hover:border-white/20 ${
        onClick ? 'cursor-pointer' : ''
      } ${className}`}
    >
      {/* Top micro accent bar */}
      <div
        className={`absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r opacity-80 ${style.barColor}`}
      />

      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
            {title}
          </p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-mono text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {value}
            </span>
          </div>

          {(subtitle || delta) && (
            <div className="mt-2 flex items-center gap-2 text-xs">
              {delta && (
                <span
                  className={`font-semibold ${
                    delta.trend === 'up'
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : delta.trend === 'down'
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-surface-500'
                  }`}
                >
                  {delta.value}
                </span>
              )}
              {subtitle && (
                <span className="truncate text-surface-500 dark:text-surface-400">
                  {subtitle}
                </span>
              )}
            </div>
          )}

          {children}
        </div>

        {renderIcon()}
      </div>
    </div>
  );
};
