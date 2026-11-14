import React from 'react';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../theme/ThemeContext';

export const ThemeToggle: React.FC<{ className?: string }> = ({ className = '' }) => {
  const { resolvedTheme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`relative inline-flex h-9 w-9 items-center justify-center rounded-lg border border-surface-200 bg-white text-surface-600 transition-colors hover:bg-surface-100 hover:text-surface-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-white/10 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800 dark:hover:text-white ${className}`}
      title={resolvedTheme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
      aria-label="Toggle theme"
    >
      {resolvedTheme === 'dark' ? (
        <Sun className="h-4 w-4 text-amber-400 transition-transform duration-200 hover:rotate-45" />
      ) : (
        <Moon className="h-4 w-4 text-surface-600 transition-transform duration-200 hover:-rotate-12" />
      )}
    </button>
  );
};
