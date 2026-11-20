import React from 'react';
import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon | React.ReactNode;
  title: string;
  description?: string;
  action?:
    | {
        label: string;
        onClick: () => void;
      }
    | React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  children,
  className = '',
}) => {
  const renderIcon = () => {
    if (React.isValidElement(icon)) {
      return icon;
    }
    const Icon = icon as LucideIcon;
    return <Icon className="h-6 w-6" />;
  };

  const renderAction = () => {
    if (!action) return null;
    if (React.isValidElement(action)) {
      return action;
    }
    const actionObj = action as { label: string; onClick: () => void };
    return (
      <button
        type="button"
        onClick={actionObj.onClick}
        className="mt-4 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-brand-500"
      >
        {actionObj.label}
      </button>
    );
  };

  return (
    <div
      className={`flex flex-col items-center justify-center rounded-xl border border-dashed border-surface-300 bg-surface-50/50 p-8 text-center dark:border-white/10 dark:bg-surface-900/40 ${className}`}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-surface-200 bg-white text-surface-400 shadow-xs dark:border-white/10 dark:bg-surface-800 dark:text-surface-400">
        {renderIcon()}
      </div>
      <h3 className="mt-4 text-sm font-semibold text-surface-900 dark:text-white">
        {title}
      </h3>
      {description && (
        <p className="mt-1 max-w-sm text-xs text-surface-500 dark:text-surface-400">
          {description}
        </p>
      )}
      {renderAction()}
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
};
