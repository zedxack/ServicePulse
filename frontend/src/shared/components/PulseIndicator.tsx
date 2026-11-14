import React from 'react';

export type PulseStatus = 'online' | 'offline' | 'warning' | 'info' | 'neutral';

interface PulseIndicatorProps {
  status: PulseStatus;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  ping?: boolean;
  className?: string;
}

export const PulseIndicator: React.FC<PulseIndicatorProps> = ({
  status,
  label,
  size = 'md',
  ping = true,
  className = '',
}) => {
  const sizeMap = {
    sm: 'h-1.5 w-1.5',
    md: 'h-2 w-2',
    lg: 'h-2.5 w-2.5',
  };

  const colorMap = {
    online: {
      dot: 'bg-emerald-500',
      ping: 'bg-emerald-400',
      text: 'text-emerald-700 dark:text-emerald-400',
    },
    offline: {
      dot: 'bg-red-500',
      ping: 'bg-red-400',
      text: 'text-red-700 dark:text-red-400',
    },
    warning: {
      dot: 'bg-amber-500',
      ping: 'bg-amber-400',
      text: 'text-amber-700 dark:text-amber-400',
    },
    info: {
      dot: 'bg-sky-500',
      ping: 'bg-sky-400',
      text: 'text-sky-700 dark:text-sky-400',
    },
    neutral: {
      dot: 'bg-surface-400',
      ping: 'bg-surface-300',
      text: 'text-surface-600 dark:text-surface-400',
    },
  };

  const colors = colorMap[status] || colorMap.neutral;
  const dotSize = sizeMap[size];

  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      <span className="relative flex items-center justify-center">
        {ping && status !== 'offline' && status !== 'neutral' && (
          <span
            className={`absolute inline-flex h-full w-full rounded-full opacity-75 motion-safe:animate-ping ${colors.ping}`}
          />
        )}
        <span className={`relative inline-flex rounded-full ${dotSize} ${colors.dot}`} />
      </span>
      {label && (
        <span className={`text-xs font-medium tracking-tight ${colors.text}`}>
          {label}
        </span>
      )}
    </div>
  );
};
