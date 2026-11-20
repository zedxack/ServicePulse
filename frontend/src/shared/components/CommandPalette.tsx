import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Activity,
  BarChart3,
  Bell,
  Building2,
  Command,
  CornerDownLeft,
  Globe,
  HardDrive,
  LifeBuoy,
  LogOut,
  Moon,
  Package,
  PieChart,
  Radio,
  Search,
  Server,
  Shield,
  ShieldAlert,
  Sun,
  User as UserIcon,
  X,
} from 'lucide-react';
import { useAuth } from '../../features/auth/AuthContext';
import { useTheme } from '../theme/ThemeContext';

export interface CommandItem {
  id: string;
  title: string;
  category: string;
  icon: React.ComponentType<{ className?: string }>;
  action: () => void;
  keywords?: string[];
  shortcut?: string;
  badge?: string;
}

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
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
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      setSearch('');
      setSelectedIndex(0);
      const timer = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  const items: CommandItem[] = useMemo(() => {
    const list: CommandItem[] = [];

    // --- 1. COMMAND & ANALYTICS (DASHBOARDS) ---
    if (user?.is_superuser || hasAnyRole(['platform_super_admin'])) {
      list.push({
        id: 'dash-platform',
        title: t('nav.platformDashboard', 'Platform Super Admin'),
        category: 'Command & Analytics',
        icon: Activity,
        action: () => navigate('/dashboard/platform'),
        keywords: ['super', 'admin', 'platform', 'tenant', 'global', 'oversight'],
        shortcut: 'D1',
      });
    }
    if (hasAnyRole(['company_admin', 'admin', 'platform_super_admin'])) {
      list.push({
        id: 'dash-company',
        title: t('nav.companyDashboard', 'Company Admin Dashboard'),
        category: 'Command & Analytics',
        icon: Building2,
        action: () => navigate('/dashboard/company'),
        keywords: ['company', 'organization', 'devices', 'users', 'quota'],
        shortcut: 'D2',
      });
    }
    if (hasAnyRole(['it_admin', 'support', 'admin', 'company_admin', 'platform_super_admin'])) {
      list.push({
        id: 'dash-sysadmin',
        title: t('nav.sysadminDashboard', 'IT Operations Cockpit'),
        category: 'Command & Analytics',
        icon: HardDrive,
        action: () => navigate('/dashboard/sysadmin'),
        keywords: ['sysadmin', 'ops', 'cockpit', 'telemetry', 'it', 'noc'],
        shortcut: 'D3',
      });
    }
    if (hasAnyRole(['executive', 'admin', 'company_admin', 'platform_super_admin'])) {
      list.push({
        id: 'dash-executive',
        title: t('nav.executiveDashboard', 'Executive & SLA Overview'),
        category: 'Command & Analytics',
        icon: PieChart,
        action: () => navigate('/dashboard/executive'),
        keywords: ['sla', 'executive', 'ceo', 'uptime', 'risk', 'kpi'],
        shortcut: 'D4',
      });
    }
    list.push({
      id: 'dash-employee',
      title: t('nav.employeeDashboard', 'Employee Portal'),
      category: 'Command & Analytics',
      icon: UserIcon,
      action: () => navigate('/dashboard/employee'),
      keywords: ['employee', 'portal', 'self-service', 'me'],
      shortcut: 'D5',
    });

    // --- 2. INFRASTRUCTURE & RMM ---
    list.push({
      id: 'infra-inventory',
      title: t('nav.inventory', 'Inventory Explorer'),
      category: 'Infrastructure & RMM',
      icon: Server,
      action: () => navigate('/inventory'),
      keywords: ['inventory', 'devices', 'servers', 'hardware', 'workstations', 'network', 'mac', 'ip'],
      shortcut: 'INV',
    });
    if (hasAnyRole(['it_admin', 'support', 'admin', 'company_admin', 'platform_super_admin'])) {
      list.push({
        id: 'infra-live-monitoring',
        title: t('nav.liveMonitoring', 'Live Telemetry Fleet & NOC Stream'),
        category: 'Infrastructure & RMM',
        icon: Radio,
        action: () => navigate('/monitoring/live'),
        keywords: ['live', 'telemetry', 'fleet', 'stream', 'websocket', 'realtime', 'ping', 'icmp'],
        shortcut: 'NOC',
      });
    }
    if (hasAnyRole(['executive', 'it_admin', 'admin', 'company_admin', 'platform_super_admin'])) {
      list.push({
        id: 'infra-analytics-sla',
        title: t('nav.analyticsSLA', 'Analytics & SLA Engine'),
        category: 'Infrastructure & RMM',
        icon: BarChart3,
        action: () => navigate('/analytics'),
        keywords: ['analytics', 'sla', 'charts', 'mttd', 'mttr', 'availability'],
        shortcut: 'SLA',
      });
    }

    // --- 3. SERVICE DESK & INCIDENTS ---
    list.push({
      id: 'ops-incidents',
      title: t('nav.incidents', 'Incident Management & War Room'),
      category: 'Service Desk & Incidents',
      icon: ShieldAlert,
      action: () => navigate('/incidents'),
      keywords: ['incidents', 'outage', 'alerts', 'failures', 'remediation', 'war room'],
      shortcut: 'INC',
    });
    list.push({
      id: 'ops-helpdesk',
      title: t('nav.helpdesk', 'Helpdesk Tickets & Dispatch'),
      category: 'Service Desk & Incidents',
      icon: LifeBuoy,
      action: () => navigate('/tickets'),
      keywords: ['tickets', 'support', 'helpdesk', 'issues', 'dispatch'],
      shortcut: 'TCK',
    });
    list.push({
      id: 'ops-alerts',
      title: t('nav.alerts', 'Alert Center & Triage'),
      category: 'Service Desk & Incidents',
      icon: Bell,
      action: () => navigate('/alerts'),
      keywords: ['alerts', 'notifications', 'bell', 'triage', 'events'],
      shortcut: 'ALT',
    });
    list.push({
      id: 'ops-software',
      title: t('nav.software', 'Software Governance Catalog'),
      category: 'Service Desk & Incidents',
      icon: Package,
      action: () => navigate('/software'),
      keywords: ['software', 'catalog', 'install', 'requests', 'packages'],
      shortcut: 'SFT',
    });

    // --- 4. GOVERNANCE & SECURITY ---
    if (user?.is_superuser || user?.is_primary_owner || hasAnyRole(['platform_super_admin'])) {
      list.push({
        id: 'sec-governance',
        title: t('command.accessGovernance', 'Access Governance & Primary Owner Approvals'),
        category: 'Governance & Security',
        icon: Shield,
        action: () => navigate('/dashboard/platform'),
        keywords: ['access', 'requests', 'owner', 'governance', 'security', 'approval', 'bootstrap'],
        shortcut: 'GOV',
        badge: 'Owner Authority',
      });
    }

    // --- 5. SYSTEM ACTIONS & PREFERENCES ---
    list.push({
      id: 'act-theme',
      title: resolvedTheme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode',
      category: 'Preferences',
      icon: resolvedTheme === 'dark' ? Sun : Moon,
      action: () => toggleTheme(),
      keywords: ['theme', 'dark', 'light', 'mode', 'display'],
      shortcut: 'THM',
    });
    list.push({
      id: 'act-lang-uz',
      title: "Tilni tanlash: O'zbekcha (UZ)",
      category: 'Preferences',
      icon: Globe,
      action: () => i18n.changeLanguage('uz'),
      keywords: ['language', 'uzbek', 'o‘zbek', 'til'],
      shortcut: 'UZ',
    });
    list.push({
      id: 'act-lang-ru',
      title: 'Выбрать язык: Русский (RU)',
      category: 'Preferences',
      icon: Globe,
      action: () => i18n.changeLanguage('ru'),
      keywords: ['language', 'russian', 'русский', 'язык'],
      shortcut: 'RU',
    });
    list.push({
      id: 'act-lang-en',
      title: 'Select Language: English (EN)',
      category: 'Preferences',
      icon: Globe,
      action: () => i18n.changeLanguage('en'),
      keywords: ['language', 'english', 'en'],
      shortcut: 'EN',
    });
    list.push({
      id: 'act-logout',
      title: t('nav.logout', 'Sign Out of Session'),
      category: 'Account',
      icon: LogOut,
      action: async () => {
        await logout();
        navigate('/login', { replace: true });
      },
      keywords: ['logout', 'signout', 'exit', 'disconnect'],
      shortcut: 'EXIT',
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
        item.shortcut?.toLowerCase().includes(q) ||
        item.keywords?.some((k) => k.toLowerCase().includes(q))
    );
  }, [items, search]);

  // Keep selected index within bounds
  useEffect(() => {
    if (selectedIndex >= filteredItems.length) {
      setSelectedIndex(Math.max(0, filteredItems.length - 1));
    }
  }, [filteredItems.length, selectedIndex]);

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current && filteredItems.length > 0) {
      const activeElement = listRef.current.children[selectedIndex] as HTMLElement;
      if (activeElement && typeof activeElement.scrollIntoView === 'function') {
        activeElement.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex, filteredItems.length]);

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
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Command Palette"
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4"
    >
      {/* Backdrop */}
      <div
        data-testid="command-palette-backdrop"
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Palette Modal Box */}
      <div
        data-testid="command-palette"
        onKeyDown={handleKeyDown}
        className="relative w-full max-w-2xl overflow-hidden rounded-xl border border-surface-200 bg-white shadow-2xl transition-all dark:border-white/10 dark:bg-surface-900"
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 border-b border-surface-200 px-4 py-3 dark:border-white/10">
          <Search className="h-4 w-4 shrink-0 text-surface-400" />
          <input
            ref={inputRef}
            data-testid="command-palette-input"
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder={t('command.searchPlaceholder', 'Type a command, route, or telemetry module...')}
            className="flex-1 bg-transparent text-sm text-surface-900 placeholder:text-surface-400 focus:outline-none dark:text-white"
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch('')}
              className="rounded p-1 text-surface-400 hover:text-surface-600 dark:hover:text-surface-200"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
          <button
            type="button"
            data-testid="command-palette-close"
            onClick={onClose}
            className="rounded p-1 text-surface-400 hover:bg-surface-100 hover:text-surface-700 dark:hover:bg-surface-800 dark:hover:text-surface-200"
            title="Close (Escape)"
          >
            <span className="sr-only">Close</span>
            <kbd className="rounded border border-surface-200 bg-surface-50 px-1.5 py-0.5 text-[10px] font-mono text-surface-500 dark:border-white/10 dark:bg-surface-800 dark:text-surface-400">
              ESC
            </kbd>
          </button>
        </div>

        {/* Results List */}
        <div
          ref={listRef}
          data-testid="command-palette-list"
          className="max-h-96 overflow-y-auto p-2 space-y-1 noc-scrollbar"
        >
          {filteredItems.length === 0 ? (
            <div className="p-8 text-center">
              <Command className="mx-auto h-8 w-8 text-surface-300 dark:text-surface-600 mb-2" />
              <p className="text-xs font-semibold text-surface-700 dark:text-surface-300">
                {t('command.noResults', 'No matching command or destination found')}
              </p>
              <p className="mt-1 text-[11px] text-surface-400 dark:text-surface-500">
                Try searching for &quot;inventory&quot;, &quot;incidents&quot;, &quot;telemetry&quot;, or &quot;theme&quot;
              </p>
            </div>
          ) : (
            filteredItems.map((item, index) => {
              const Icon = item.icon;
              const isSelected = index === selectedIndex;
              return (
                <button
                  key={item.id}
                  type="button"
                  data-testid="command-palette-item"
                  data-index={index}
                  onClick={() => {
                    item.action();
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs transition-all ${
                    isSelected
                      ? 'bg-brand-50/90 text-brand-950 ring-1 ring-brand-500/30 dark:bg-brand-950/70 dark:text-brand-200 dark:ring-brand-500/40'
                      : 'text-surface-700 hover:bg-surface-50 dark:text-surface-300 dark:hover:bg-surface-800/60'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md border ${
                        isSelected
                          ? 'border-brand-300 bg-white text-brand-600 dark:border-brand-700 dark:bg-surface-900 dark:text-brand-300'
                          : 'border-surface-200 bg-surface-50 text-surface-500 dark:border-white/5 dark:bg-surface-800 dark:text-surface-400'
                      }`}
                    >
                      <Icon className="h-3.5 w-3.5" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="truncate font-medium">{item.title}</p>
                        {item.badge && (
                          <span className="rounded bg-amber-100 px-1.5 py-0.2 text-[9px] font-bold text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 ring-1 ring-amber-500/30 font-mono">
                            {item.badge}
                          </span>
                        )}
                      </div>
                      <p className="truncate text-[10px] text-surface-400 dark:text-surface-500">
                        {item.category}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 ml-3">
                    {item.shortcut && (
                      <span className="hidden sm:inline-block rounded border border-surface-200 bg-surface-100 px-1.5 py-0.5 text-[9px] font-mono font-medium text-surface-600 dark:border-white/10 dark:bg-surface-800 dark:text-surface-400">
                        {item.shortcut}
                      </span>
                    )}
                    {isSelected && (
                      <span className="flex items-center gap-1 font-mono text-[10px] text-brand-700 dark:text-brand-300">
                        <CornerDownLeft className="h-3 w-3" />
                        <span>Select</span>
                      </span>
                    )}
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Technical SysAdmin Footer */}
        <div className="flex items-center justify-between border-t border-surface-200 bg-surface-50 px-4 py-2.5 text-[10px] text-surface-500 dark:border-white/10 dark:bg-surface-950 dark:text-surface-400">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="rounded border border-surface-200 bg-white px-1 py-0.2 text-[9px] font-mono dark:border-white/10 dark:bg-surface-900">
                ↑↓
              </kbd>
              <span>{t('command.navigate', 'Navigate')}</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="rounded border border-surface-200 bg-white px-1 py-0.2 text-[9px] font-mono dark:border-white/10 dark:bg-surface-900">
                ↵
              </kbd>
              <span>{t('command.select', 'Execute')}</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="rounded border border-surface-200 bg-white px-1 py-0.2 text-[9px] font-mono dark:border-white/10 dark:bg-surface-900">
                ESC
              </kbd>
              <span>{t('command.close', 'Exit')}</span>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="font-mono text-[10px] tracking-wider text-surface-400 dark:text-surface-500 uppercase">
              CLI / NOC DISPATCH
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
