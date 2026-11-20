import React, { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Activity,
  BarChart3,
  Bell,
  Building2,
  ChevronLeft,
  ChevronRight,
  Command,
  HardDrive,
  LayoutDashboard,
  LifeBuoy,
  LogOut,
  Menu,
  Package,
  PieChart,
  Radio,
  Search,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  User as UserIcon,
  X,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../features/auth/AuthContext';
import { LanguageSwitcher } from '../../shared/components/LanguageSwitcher';
import { ThemeToggle } from '../../shared/components/ThemeToggle';
import { CommandPalette } from '../../shared/components/CommandPalette';
import { getUnreadAlertCount } from '../../shared/api/alerts';
import { useRealtimeMonitoring } from '../../features/monitoring/useRealtimeMonitoring';

export const AppLayout: React.FC = () => {
  const { t } = useTranslation();
  const { user, logout, hasAnyRole } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  // Maintain real-time WebSocket connection across layout
  const { status } = useRealtimeMonitoring(Boolean(user));
  const isConnected = status === 'connected';

  const { data: unreadData } = useQuery({
    queryKey: ['unread-alerts-count'],
    queryFn: getUnreadAlertCount,
    refetchInterval: 30000,
    enabled: Boolean(user),
  });
  const unreadCount = unreadData?.unread_count ?? 0;

  // Global Ctrl+K / Cmd+K shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  // 1. COMMAND & ANALYTICS (DASHBOARDS)
  const commandAndAnalyticsItems = [
    {
      to: '/dashboard/platform',
      label: t('nav.platformDashboard', 'Platform Super Admin'),
      icon: Activity,
      visible: user?.is_superuser || hasAnyRole(['platform_super_admin']),
      badge: 'Platform',
    },
    {
      to: '/dashboard/company',
      label: t('nav.companyDashboard', 'Company Admin'),
      icon: Building2,
      visible: hasAnyRole(['company_admin', 'admin', 'platform_super_admin']),
      badge: 'Company',
    },
    {
      to: '/dashboard/sysadmin',
      label: t('nav.sysadminDashboard', 'Operations Cockpit'),
      icon: HardDrive,
      visible: hasAnyRole(['it_admin', 'support', 'admin', 'company_admin', 'platform_super_admin']),
      badge: 'Ops',
    },
    {
      to: '/dashboard/executive',
      label: t('nav.executiveDashboard', 'Executive & SLA'),
      icon: PieChart,
      visible: hasAnyRole(['executive', 'admin', 'company_admin', 'platform_super_admin']),
      badge: 'SLA',
    },
    {
      to: '/dashboard/employee',
      label: t('nav.employeeDashboard', 'Employee Portal'),
      icon: UserIcon,
      visible: true,
      badge: 'Portal',
    },
  ];

  // 2. INFRASTRUCTURE & RMM
  const infrastructureItems = [
    {
      to: '/inventory',
      label: t('nav.inventory', 'Inventory Explorer'),
      icon: Server,
      visible: true,
    },
    {
      to: '/monitoring/live',
      label: t('nav.liveMonitoring', 'Live Monitoring'),
      icon: Radio,
      visible: hasAnyRole(['it_admin', 'support', 'admin', 'company_admin', 'platform_super_admin']),
    },
    {
      to: '/analytics',
      label: t('nav.analyticsSLA', 'Analytics & SLA'),
      icon: BarChart3,
      visible: hasAnyRole(['executive', 'it_admin', 'admin', 'company_admin', 'platform_super_admin']),
    },
  ];

  // 3. SERVICE DESK & INCIDENTS
  const serviceDeskItems = [
    {
      to: '/incidents',
      label: t('nav.incidents', 'Incident Management'),
      icon: ShieldAlert,
      visible: true,
    },
    {
      to: '/tickets',
      label: t('nav.helpdesk', 'Helpdesk Tickets'),
      icon: LifeBuoy,
      visible: true,
    },
    {
      to: '/alerts',
      label: t('nav.alerts', 'Alert Center'),
      icon: Bell,
      visible: true,
      badgeCount: unreadCount,
    },
    {
      to: '/software',
      label: t('nav.software', 'Software Approval'),
      icon: Package,
      visible: true,
    },
  ];

  // 4. GOVERNANCE & SECURITY
  const isPrimaryOwner = Boolean(
    user?.is_primary_owner || (user?.is_superuser && hasAnyRole(['platform_super_admin']))
  );

  const governanceItems = [
    {
      to: '/dashboard/platform',
      label: t('nav.accessGovernance', 'Access Governance'),
      icon: ShieldCheck,
      visible: Boolean(user?.is_superuser || user?.is_primary_owner || hasAnyRole(['platform_super_admin'])),
      badge: 'Owner',
    },
  ];

  // Dynamic breadcrumb text
  const getBreadcrumb = () => {
    const path = location.pathname;
    if (path.includes('/dashboard/platform')) return 'Platform Super Admin';
    if (path.includes('/dashboard/company')) return 'Company Administrator';
    if (path.includes('/dashboard/sysadmin')) return 'IT Operations Cockpit';
    if (path.includes('/dashboard/executive')) return 'Executive & SLA Strategy';
    if (path.includes('/dashboard/employee')) return 'Employee Self-Service Portal';
    if (path.includes('/inventory')) return 'Inventory Explorer';
    if (path.includes('/incidents')) return 'Incident Response & Remediation';
    if (path.includes('/tickets')) return 'ITSM Helpdesk';
    if (path.includes('/software')) return 'Software Governance Catalog';
    if (path.includes('/monitoring/live')) return 'Real-Time Telemetry Fleet';
    if (path.includes('/analytics')) return 'Availability Analytics & SLA';
    if (path.includes('/alerts')) return 'Operations Alert Center';
    return 'Command Center';
  };

  const getPrimaryRoleBadge = () => {
    if (isPrimaryOwner) {
      return {
        label: 'PRIMARY OWNER',
        isOwner: true,
        className: 'border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-300 ring-1 ring-amber-500/30',
      };
    }
    if (user?.is_superuser || hasAnyRole(['platform_super_admin'])) {
      return {
        label: 'SUPER ADMIN',
        isOwner: false,
        className: 'border-purple-500/40 bg-purple-500/10 text-purple-700 dark:text-purple-300 ring-1 ring-purple-500/20',
      };
    }
    if (hasAnyRole(['company_admin'])) {
      return {
        label: 'ORG ADMIN',
        isOwner: false,
        className: 'border-blue-500/40 bg-blue-500/10 text-blue-700 dark:text-blue-300',
      };
    }
    if (hasAnyRole(['it_admin'])) {
      return {
        label: 'SYSADMIN',
        isOwner: false,
        className: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300',
      };
    }
    if (hasAnyRole(['support'])) {
      return {
        label: 'SUPPORT',
        isOwner: false,
        className: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
      };
    }
    if (hasAnyRole(['executive'])) {
      return {
        label: 'EXECUTIVE',
        isOwner: false,
        className: 'border-indigo-500/40 bg-indigo-500/10 text-indigo-700 dark:text-indigo-300',
      };
    }
    return {
      label: 'STAFF',
      isOwner: false,
      className: 'border-surface-300 bg-surface-100 text-surface-600 dark:border-white/10 dark:bg-surface-800 dark:text-surface-400',
    };
  };

  const roleBadge = getPrimaryRoleBadge();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-surface-50 text-surface-900 transition-colors duration-200 dark:bg-[#090d16] dark:text-white">
      {/* Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />

      {/* Desktop Collapsible Categorized NOC Sidebar */}
      <aside
        data-testid="noc-sidebar"
        className={`hidden flex-col border-r border-surface-200 bg-white transition-all duration-300 dark:border-white/10 dark:bg-surface-900 md:flex ${
          isSidebarCollapsed ? 'w-16' : 'w-64'
        }`}
      >
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between border-b border-surface-200 px-4 dark:border-white/10">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-brand-600 to-sky-400 text-white shadow-sm shadow-brand-500/25">
              <Activity className="h-5 w-5" />
              <span className={`absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full border border-white dark:border-surface-900 ${isConnected ? 'bg-emerald-400' : 'bg-amber-400'}`} />
            </div>
            {!isSidebarCollapsed && (
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <h1 className="truncate text-sm font-bold tracking-tight text-surface-900 dark:text-white">
                    {t('app.title', 'ServicePulse')}
                  </h1>
                  <span className="rounded bg-brand-50 px-1 py-0.2 text-[9px] font-bold text-brand-700 ring-1 ring-brand-500/20 dark:bg-brand-950/60 dark:text-brand-300 font-mono">
                    NOC
                  </span>
                </div>
                <p className="truncate text-[10px] font-mono text-surface-500 dark:text-surface-400">
                  Command Center v1.0
                </p>
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            className="rounded-lg p-1 text-surface-400 hover:bg-surface-100 hover:text-surface-700 dark:hover:bg-surface-800 dark:hover:text-surface-200"
            title={isSidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            {isSidebarCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Navigation Sections */}
        <div className="flex-1 overflow-y-auto px-2.5 py-3 space-y-4 noc-scrollbar">
          {/* Section 1: Command & Analytics */}
          <div>
            {!isSidebarCollapsed && (
              <div className="mb-1.5 px-2.5 text-[9px] font-mono font-bold uppercase tracking-wider text-surface-400 dark:text-surface-500">
                COMMAND &amp; ANALYTICS
              </div>
            )}
            <nav className="space-y-1">
              {commandAndAnalyticsItems
                .filter((item) => item.visible)
                .map((item) => {
                  const Icon = item.icon;
                  const isPrimary =
                    user?.primary_dashboard && item.to.includes(user.primary_dashboard);
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      title={isSidebarCollapsed ? item.label : undefined}
                      className={({ isActive }) =>
                        `flex items-center ${
                          isSidebarCollapsed ? 'justify-center px-2 py-2.5' : 'justify-between px-3 py-2'
                        } rounded-lg text-xs font-semibold transition-all ${
                          isActive
                            ? 'bg-brand-50 text-brand-700 shadow-xs dark:bg-brand-950/70 dark:text-brand-300 dark:ring-1 dark:ring-brand-500/30'
                            : 'text-surface-600 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-800/60 dark:hover:text-white'
                        }`
                      }
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className="h-4 w-4 shrink-0" />
                        {!isSidebarCollapsed && <span className="truncate">{item.label}</span>}
                      </div>
                      {!isSidebarCollapsed && isPrimary && (
                        <span className="rounded bg-brand-100 px-1.5 py-0.2 text-[9px] font-mono font-bold text-brand-800 dark:bg-brand-900/60 dark:text-brand-300">
                          {t('nav.myDashboard', 'Primary')}
                        </span>
                      )}
                    </NavLink>
                  );
                })}
            </nav>
          </div>

          {/* Section 2: Infrastructure & RMM */}
          <div>
            {!isSidebarCollapsed && (
              <div className="mb-1.5 px-2.5 text-[9px] font-mono font-bold uppercase tracking-wider text-surface-400 dark:text-surface-500">
                INFRASTRUCTURE &amp; RMM
              </div>
            )}
            <nav className="space-y-1">
              {infrastructureItems
                .filter((item) => item.visible)
                .map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      title={isSidebarCollapsed ? item.label : undefined}
                      className={({ isActive }) =>
                        `flex items-center ${
                          isSidebarCollapsed ? 'justify-center px-2 py-2.5' : 'justify-between px-3 py-2'
                        } rounded-lg text-xs font-semibold transition-all ${
                          isActive
                            ? 'bg-brand-50 text-brand-700 shadow-xs dark:bg-brand-950/70 dark:text-brand-300 dark:ring-1 dark:ring-brand-500/30'
                            : 'text-surface-600 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-800/60 dark:hover:text-white'
                        }`
                      }
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className="h-4 w-4 shrink-0" />
                        {!isSidebarCollapsed && <span className="truncate">{item.label}</span>}
                      </div>
                    </NavLink>
                  );
                })}
            </nav>
          </div>

          {/* Section 3: Service Desk & Incidents */}
          <div>
            {!isSidebarCollapsed && (
              <div className="mb-1.5 px-2.5 text-[9px] font-mono font-bold uppercase tracking-wider text-surface-400 dark:text-surface-500">
                SERVICE DESK &amp; INCIDENTS
              </div>
            )}
            <nav className="space-y-1">
              {serviceDeskItems
                .filter((item) => item.visible)
                .map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      title={isSidebarCollapsed ? item.label : undefined}
                      className={({ isActive }) =>
                        `flex items-center ${
                          isSidebarCollapsed ? 'justify-center px-2 py-2.5' : 'justify-between px-3 py-2'
                        } rounded-lg text-xs font-semibold transition-all ${
                          isActive
                            ? 'bg-brand-50 text-brand-700 shadow-xs dark:bg-brand-950/70 dark:text-brand-300 dark:ring-1 dark:ring-brand-500/30'
                            : 'text-surface-600 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-800/60 dark:hover:text-white'
                        }`
                      }
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className="h-4 w-4 shrink-0" />
                        {!isSidebarCollapsed && <span className="truncate">{item.label}</span>}
                      </div>
                      {Boolean(item.badgeCount && item.badgeCount > 0) && (
                        <span className="rounded-full bg-red-600 px-1.5 py-0.2 text-[10px] font-mono font-bold text-white shadow-xs">
                          {item.badgeCount}
                        </span>
                      )}
                    </NavLink>
                  );
                })}
            </nav>
          </div>

          {/* Section 4: Governance & Security (Owner / Super Admin) */}
          {governanceItems.some((item) => item.visible) && (
            <div>
              {!isSidebarCollapsed && (
                <div className="mb-1.5 px-2.5 text-[9px] font-mono font-bold uppercase tracking-wider text-surface-400 dark:text-surface-500">
                  GOVERNANCE &amp; SECURITY
                </div>
              )}
              <nav className="space-y-1">
                {governanceItems
                  .filter((item) => item.visible)
                  .map((item) => {
                    const Icon = item.icon;
                    return (
                      <NavLink
                        key={item.to}
                        to={item.to}
                        title={isSidebarCollapsed ? item.label : undefined}
                        className={({ isActive }) =>
                          `flex items-center ${
                            isSidebarCollapsed ? 'justify-center px-2 py-2.5' : 'justify-between px-3 py-2'
                          } rounded-lg text-xs font-semibold transition-all ${
                            isActive
                              ? 'bg-brand-50 text-brand-700 shadow-xs dark:bg-brand-950/70 dark:text-brand-300 dark:ring-1 dark:ring-brand-500/30'
                              : 'text-surface-600 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-800/60 dark:hover:text-white'
                          }`
                        }
                      >
                        <div className="flex items-center gap-2.5">
                          <Icon className="h-4 w-4 shrink-0 text-amber-500" />
                          {!isSidebarCollapsed && <span className="truncate">{item.label}</span>}
                        </div>
                        {!isSidebarCollapsed && item.badge && (
                          <span className="rounded bg-amber-100 px-1.5 py-0.2 text-[9px] font-mono font-bold text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 ring-1 ring-amber-500/20">
                            {item.badge}
                          </span>
                        )}
                      </NavLink>
                    );
                  })}
              </nav>
            </div>
          )}
        </div>

        {/* Compact Technical System Status Footer in Sidebar */}
        {!isSidebarCollapsed ? (
          <div
            data-testid="noc-engine-status"
            className="border-t border-surface-200 bg-surface-50/70 p-3 dark:border-white/10 dark:bg-surface-950/50"
          >
            <div className="flex items-center justify-between text-[10px] font-mono">
              <div className="flex items-center gap-1.5">
                <span className={isConnected ? 'status-dot-online' : 'status-dot-warning'} />
                <span className="font-bold text-surface-800 dark:text-surface-200">
                  {isConnected ? 'ENGINE: NOMINAL' : 'ENGINE: SYNCING'}
                </span>
              </div>
              <span className="rounded bg-surface-200/60 px-1.5 py-0.2 text-[9px] font-mono text-surface-600 dark:bg-surface-800 dark:text-surface-400">
                v1.0.0
              </span>
            </div>
            <div className="mt-1.5 flex items-center justify-between text-[9px] font-mono text-surface-400 dark:text-surface-500">
              <span>STREAM: {isConnected ? 'WSS' : 'POLL'}</span>
              <span>{user?.organization_id ? `TENANT #${user.organization_id}` : 'GLOBAL NOC'}</span>
            </div>
          </div>
        ) : (
          <div
            data-testid="noc-engine-status-collapsed"
            className="border-t border-surface-200 p-2 text-center dark:border-white/10"
            title={isConnected ? 'ENGINE: NOMINAL (v1.0.0)' : 'ENGINE: SYNCING'}
          >
            <span className={isConnected ? 'status-dot-online' : 'status-dot-warning'} />
          </div>
        )}

        {/* User Profile & Logout Footer */}
        <div className="border-t border-surface-200 p-3 dark:border-white/10">
          {!isSidebarCollapsed ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface-100 text-xs font-bold text-brand-700 ring-1 ring-surface-300 dark:bg-surface-800 dark:text-brand-400 dark:ring-white/10">
                  {user?.full_name?.charAt(0) || 'U'}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-surface-900 dark:text-white">
                    {user?.full_name}
                  </p>
                  <p className="truncate text-[10px] font-mono text-surface-500 dark:text-surface-400">
                    {user?.email}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-surface-200 bg-surface-50 py-1.5 text-xs font-medium text-surface-700 transition-colors hover:border-red-200 hover:bg-red-50 hover:text-red-700 dark:border-white/10 dark:bg-surface-800 dark:text-surface-300 dark:hover:border-red-900 dark:hover:bg-red-950/40 dark:hover:text-red-400"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>{t('nav.logout', 'Sign Out')}</span>
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleLogout}
              title={t('nav.logout', 'Sign Out')}
              className="flex h-9 w-full items-center justify-center rounded-lg text-surface-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/40 dark:hover:text-red-400"
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>
      </aside>

      {/* Mobile Drawer Overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="relative flex w-72 max-w-[85%] flex-col bg-white shadow-2xl dark:bg-surface-900">
            <div className="flex h-16 items-center justify-between border-b border-surface-200 px-4 dark:border-white/10">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-tr from-brand-600 to-sky-400 text-white shadow-xs">
                  <Activity className="h-4 w-4" />
                </div>
                <span className="font-bold text-surface-900 dark:text-white">
                  {t('app.title', 'ServicePulse')}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded-lg p-1.5 text-surface-500 hover:bg-surface-100 dark:hover:bg-surface-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-4 noc-scrollbar">
              <nav className="space-y-1">
                {[
                  ...commandAndAnalyticsItems.filter((i) => i.visible),
                  ...infrastructureItems.filter((i) => i.visible),
                  ...serviceDeskItems.filter((i) => i.visible),
                  ...governanceItems.filter((i) => i.visible),
                ].map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={() => setMobileMenuOpen(false)}
                      className={({ isActive }) =>
                        `flex items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold ${
                          isActive
                            ? 'bg-brand-50 text-brand-700 dark:bg-brand-950/70 dark:text-brand-300'
                            : 'text-surface-600 hover:bg-surface-50 dark:text-surface-400 dark:hover:bg-surface-800/60'
                        }`
                      }
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className="h-4 w-4" />
                        <span>{item.label}</span>
                      </div>
                    </NavLink>
                  );
                })}
              </nav>
            </div>

            <div className="border-t border-surface-200 p-3 dark:border-white/10">
              <button
                type="button"
                onClick={handleLogout}
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-surface-200 bg-surface-50 py-2 text-xs font-medium text-surface-700 dark:border-white/10 dark:bg-surface-800 dark:text-surface-300"
              >
                <LogOut className="h-4 w-4" />
                <span>{t('nav.logout', 'Sign Out')}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Viewport */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Header Live NOC Command Bar */}
        <header
          data-testid="noc-header"
          className="flex h-16 items-center justify-between border-b border-surface-200 bg-white/80 px-4 md:px-6 backdrop-blur-md dark:border-white/10 dark:bg-surface-900/80"
        >
          {/* Left: Mobile hamburger + Contextual Breadcrumbs */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              className="rounded-lg p-2 text-surface-600 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-800 md:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-2 text-xs text-surface-500 dark:text-surface-400">
              <LayoutDashboard className="h-4 w-4 text-surface-400 dark:text-surface-500" />
              <span className="hidden sm:inline">{t('nav.dashboard', 'Operations')}</span>
              <ChevronRight className="h-3.5 w-3.5 text-surface-300 dark:text-surface-600" />
              <span className="font-semibold text-surface-900 dark:text-white">
                {getBreadcrumb()}
              </span>
            </div>
          </div>

          {/* Center: Quick Command Palette Trigger Button */}
          <div className="hidden lg:flex items-center">
            <button
              type="button"
              data-testid="command-palette-trigger"
              onClick={() => setIsCommandPaletteOpen(true)}
              className="flex items-center gap-2.5 rounded-lg border border-surface-200 bg-surface-50 px-3 py-1.5 text-xs text-surface-500 transition-colors hover:border-surface-300 hover:text-surface-700 dark:border-white/10 dark:bg-surface-800/60 dark:text-surface-400 dark:hover:border-white/20 dark:hover:text-surface-200"
            >
              <Search className="h-3.5 w-3.5" />
              <span className="hidden xl:inline">Search commands, telemetry...</span>
              <span className="xl:hidden">Search...</span>
              <kbd className="flex items-center gap-0.5 rounded border border-surface-200 bg-white px-1.5 py-0.2 text-[10px] font-mono font-medium text-surface-500 dark:border-white/10 dark:bg-surface-900 dark:text-surface-400">
                <Command className="h-3 w-3" />K
              </kbd>
            </button>
          </div>

          {/* Right: Operational Status Indicators & Controls */}
          <div className="flex items-center gap-2.5 sm:gap-3">
            {/* Live System Telemetry Status Pill */}
            <div
              data-testid="noc-telemetry-pill"
              className="hidden sm:flex items-center gap-2 rounded-full border border-surface-200 bg-surface-50 px-2.5 py-1 text-[11px] font-mono font-medium text-surface-700 dark:border-white/10 dark:bg-surface-800/60 dark:text-surface-300"
              title={isConnected ? 'Real-Time WebSocket Feed Nominal' : 'WebSocket Reconnecting...'}
            >
              <span className={isConnected ? 'status-dot-online' : 'status-dot-warning'} />
              <span className="tracking-tight">{isConnected ? 'SYSTEM NOMINAL' : 'TELEMETRY SYNC'}</span>
            </div>

            {/* Active Tenant / Organization Badge */}
            {user?.organization_id && (
              <div
                data-testid="tenant-badge"
                className="hidden md:flex items-center gap-1.5 rounded-full border border-surface-200 bg-surface-100/60 px-2.5 py-1 text-[11px] font-mono font-medium text-surface-700 dark:border-white/10 dark:bg-surface-800/60 dark:text-surface-300"
              >
                <Building2 className="h-3.5 w-3.5 text-surface-500" />
                <span>ORG #{user.organization_id}</span>
              </div>
            )}

            {/* User Role Badge (Authoritative Primary Owner or Role) */}
            <div
              data-testid="user-role-badge"
              className={`hidden sm:inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-mono font-bold tracking-wider ${roleBadge.className}`}
              title={roleBadge.isOwner ? 'Platform Primary Owner: Supreme Administrative Authority' : `Role: ${roleBadge.label}`}
            >
              {roleBadge.isOwner ? (
                <>
                  <ShieldCheck className="h-3 w-3 text-amber-500 dark:text-amber-400 shrink-0" />
                  <span>PRIMARY OWNER</span>
                </>
              ) : (
                <>
                  <Shield className="h-3 w-3 shrink-0" />
                  <span>{roleBadge.label}</span>
                </>
              )}
            </div>

            {/* Alert Center Trigger */}
            <button
              type="button"
              data-testid="alert-center-trigger"
              onClick={() => navigate('/alerts')}
              className="relative rounded-lg p-2 text-surface-600 transition-colors hover:bg-surface-100 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-800 dark:hover:text-white"
              title={t('nav.alerts', 'Alert Center')}
            >
              <Bell className="h-4 w-4" />
              {unreadCount > 0 && (
                <span className="absolute top-1.5 right-1.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-600 px-1 text-[9px] font-mono font-bold text-white shadow-xs">
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </button>

            {/* Theme & Language Selectors */}
            <ThemeToggle />
            <LanguageSwitcher />
          </div>
        </header>

        {/* Main Scrollable Viewport */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 noc-scrollbar">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
