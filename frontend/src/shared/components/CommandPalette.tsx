import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Activity,
  BarChart3,
  Bell,
  Building2,
  Check,
  HardDrive,
  LifeBuoy,
  LogOut,
  Moon,
  Package,
  PieChart,
  Radio,
  Search,
  Server,
  ShieldAlert,
  Sun,
  User as UserIcon,
  X,
} from 'lucide-react';
import { useAuth } from '../../features/auth/AuthContext';
import { useTheme } from '../theme/ThemeContext';

interface CommandItem {
  id: string;
  title: string;
  category: string;
  icon: React.ComponentType<{ className?: string }>;
  action: () => void;
  keywords?: string[];
  shortcut?: string;
}

export const CommandPalette: React.FC<{ isOpen: boolean; onClose: () => void }> = ({
  isOpen,
  onClose,
}) => {
  const { t, i18n } = useTranslation();
  const { user, logout, hasAnyRole } = useAuth();
  const { resolvedTheme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setSearch('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const items: CommandItem[] = useMemo(() => {
    const list: CommandItem[] = [];

    // Dashboards
    if (user?.is_superuser || hasAnyRole(['platform_super_admin'])) {
      list.push({
        id: 'dash-platform',
        title: t('nav.platformDashboard', 'Platform Super Admin'),
        category: t('nav.dashboard', 'Dashboards'),
        icon: Activity,
        action: () => navigate('/dashboard/platform'),
        keywords: ['super', 'admin', 'platform', 'tenant'],
      });
    }
    if (hasAnyRole(['company_admin', 'admin', 'platform_super_admin'])) {
      list.push({
        id: 'dash-company',
        title: t('nav.companyDashboard', 'Company Admin Dashboard'),
        category: t('nav.dashboard', 'Dashboards'),
        icon: Building2,
        action: () => navigate('/dashboard/company'),
        keywords: ['company', 'organization', 'devices', 'users'],
      });
    }
    if (hasAnyRole(['it_admin', 'support', 'admin', 'company_admin', 'platform_super_admin'])) {
      list.push({
        id: 'dash-sysadmin',
        title: t('nav.sysadminDashboard', 'IT Operations Cockpit'),
        category: t('nav.dashboard', 'Dashboards'),
        icon: HardDrive,
        action: () => navigate('/dashboard/sysadmin'),
        keywords: ['sysadmin', 'ops', 'cockpit', 'telemetry', 'it'],
      });
    }
    if (hasAnyRole(['executive', 'admin', 'company_admin', 'platform_super_admin'])) {
      list.push({
        id: 'dash-executive',
        title: t('nav.executiveDashboard', 'Executive & SLA Overview'),
        category: t('nav.dashboard', 'Dashboards'),
        icon: PieChart,
        action: () => navigate('/dashboard/executive'),
        keywords: ['sla', 'executive', 'ceo', 'uptime', 'risk'],
      });
    }
    list.push({
      id: 'dash-employee',
      title: t('nav.employeeDashboard', 'Employee Portal'),
      category: t('nav.dashboard', 'Dashboards'),
      icon: UserIcon,
      action: () => navigate('/dashboard/employee'),
      keywords: ['employee', 'portal', 'self-service', 'me'],
    });

    // Operations
    list.push({
      id: 'op-inventory',
      title: t('nav.inventory', 'Inventory Explorer'),
      category: 'Operations',
      icon: Server,
      action: () => navigate('/inventory'),
      keywords: ['inventory', 'devices', 'servers', 'hardware'],
    });
    list.push({
      id: 'op-incidents',
      title: t('nav.incidents', 'Incident Management'),
      category: 'Operations',
      icon: ShieldAlert,
      action: () => navigate('/incidents'),
      keywords: ['incidents', 'outage', 'alerts', 'failures'],
    });
    list.push({
      id: 'op-helpdesk',
      title: t('nav.helpdesk', 'Helpdesk Tickets'),
      category: 'Operations',
      icon: LifeBuoy,
      action: () => navigate('/tickets'),
      keywords: ['tickets', 'support', 'helpdesk', 'issues'],
    });
    list.push({
      id: 'op-software',
      title: t('nav.software', 'Software Approval'),
      category: 'Operations',
      icon: Package,
      action: () => navigate('/software'),
      keywords: ['software', 'catalog', 'install', 'requests'],
    });

    // Monitoring & Realtime
    list.push({
      id: 'mon-live',
      title: t('nav.liveMonitoring', 'Live Telemetry & Fleet'),
      category: 'Monitoring',
      icon: Radio,
      action: () => navigate('/monitoring/live'),
      keywords: ['live', 'telemetry', 'fleet', 'stream', 'websocket'],
    });
    list.push({
      id: 'mon-analytics',
      title: t('nav.analyticsSLA', 'Analytics & SLA Engine'),
      category: 'Monitoring',
      icon: BarChart3,
      action: () => navigate('/analytics'),
      keywords: ['analytics', 'sla', 'charts', 'mttd', 'mttr'],
    });
    list.push({
      id: 'mon-alerts',
      title: t('nav.alerts', 'Alert Center'),
      category: 'Monitoring',
      icon: Bell,
      action: () => navigate('/alerts'),
      keywords: ['alerts', 'notifications', 'bell'],
    });

    // Actions & Preferences
    list.push({
      id: 'pref-theme',
      title: resolvedTheme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme',
      category: 'Preferences',
      icon: resolvedTheme === 'dark' ? Sun : Moon,
      action: () => toggleTheme(),
      keywords: ['theme', 'dark', 'light', 'mode'],
    });
    list.push({
      id: 'pref-lang-uz',
      title: "Tilni o'zgartirish: O'zbekcha",
      category: 'Preferences',
      icon: Check,
      action: () => i18n.changeLanguage('uz'),
      keywords: ['language', 'uzbek', 'o‘zbek'],
    });
    list.push({
      id: 'pref-lang-ru',
      title: 'Сменить язык: Русский',
      category: 'Preferences',
      icon: Check,
      action: () => i18n.changeLanguage('ru'),
      keywords: ['language', 'russian', 'русский'],
    });
    list.push({
      id: 'pref-lang-en',
      title: 'Change Language: English',
      category: 'Preferences',
      icon: Check,
      action: () => i18n.changeLanguage('en'),
      keywords: ['language', 'english'],
    });
    list.push({
      id: 'action-logout',
      title: t('nav.logout', 'Sign Out'),
      category: 'Account',
      icon: LogOut,
      action: async () => {
        await logout();
        navigate('/login', { replace: true });
      },
      keywords: ['logout', 'signout', 'exit'],
    });

    return list;
  }, [user, hasAnyRole, t, i18n, resolvedTheme, toggleTheme, logout, navigate]);

  const filteredItems = useMemo(() => {
    if (!search.trim()) return items;
    const q = search.toLowerCase().trim();
    return items.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q) ||
        item.keywords?.some((k) => k.toLowerCase().includes(q))
    );
  }, [items, search]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % (filteredItems.length || 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) =>
        prev <= 0 ? (filteredItems.length || 1) - 1 : prev - 1
      );
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const target = filteredItems[selectedIndex];
      if (target) {
        target.action();
        onClose();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 sm:pt-28">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div
        className="relative w-full max-w-xl overflow-hidden rounded-xl border border-surface-200 bg-white shadow-2xl transition-all dark:border-white/10 dark:bg-surface-900"
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar */}
        <div className="flex items-center border-b border-surface-200 px-4 py-3 dark:border-white/10">
          <Search className="h-4 w-4 shrink-0 text-surface-400" />
          <input
            ref={inputRef}
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder={t('command.searchPlaceholder', 'Type a command or jump to page...')}
            className="flex-1 bg-transparent px-3 text-sm text-surface-900 placeholder:text-surface-400 focus:outline-none dark:text-white"
          />
          <button
            onClick={onClose}
            className="rounded p-1 text-surface-400 hover:bg-surface-100 hover:text-surface-700 dark:hover:bg-surface-800"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto p-2">
          {filteredItems.length === 0 ? (
            <div className="p-8 text-center text-xs text-surface-500">
              No matching commands or destinations found.
            </div>
          ) : (
            filteredItems.map((item, index) => {
              const Icon = item.icon;
              const isSelected = index === selectedIndex;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    item.action();
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs transition-colors ${
                    isSelected
                      ? 'bg-brand-50 text-brand-900 dark:bg-brand-950/60 dark:text-brand-300'
                      : 'text-surface-700 hover:bg-surface-50 dark:text-surface-300 dark:hover:bg-surface-800/60'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`flex h-7 w-7 items-center justify-center rounded-md border ${
                        isSelected
                          ? 'border-brand-200 bg-white text-brand-600 dark:border-brand-800 dark:bg-surface-900 dark:text-brand-400'
                          : 'border-surface-200 bg-surface-50 text-surface-500 dark:border-white/5 dark:bg-surface-800 dark:text-surface-400'
                      }`}
                    >
                      <Icon className="h-3.5 w-3.5" />
                    </div>
                    <div>
                      <p className="font-semibold">{item.title}</p>
                      <p className="text-[10px] text-surface-400 dark:text-surface-500">
                        {item.category}
                      </p>
                    </div>
                  </div>
                  {isSelected && (
                    <span className="font-mono text-[10px] text-brand-600 dark:text-brand-400">
                      Press Enter ↵
                    </span>
                  )}
                </button>
              );
            })
          )}
        </div>

        {/* Footer shortcuts helper */}
        <div className="flex items-center justify-between border-t border-surface-200 bg-surface-50 px-4 py-2 text-[10px] text-surface-400 dark:border-white/10 dark:bg-surface-950">
          <div className="flex items-center gap-2">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <span className="font-mono">ServicePulse CLI Command Bar</span>
        </div>
      </div>
    </div>
  );
};
