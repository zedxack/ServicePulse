import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Activity,
  Building2,
  ChevronRight,
  HardDrive,
  LayoutDashboard,
  LifeBuoy,
  LogOut,
  Menu,
  Package,
  PieChart,
  Server,
  ShieldAlert,
  User as UserIcon,
  X,
} from 'lucide-react';
import { useAuth } from '../../features/auth/AuthContext';
import { LanguageSwitcher } from '../../shared/components/LanguageSwitcher';

export const AppLayout: React.FC = () => {
  const { t } = useTranslation();
  const { user, logout, hasAnyRole } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const navItems = [
    {
      to: '/dashboard/platform',
      label: t('nav.platformDashboard'),
      icon: Activity,
      visible: user?.is_superuser || hasAnyRole(['platform_super_admin']),
      badge: 'Platform',
    },
    {
      to: '/dashboard/company',
      label: t('nav.companyDashboard'),
      icon: Building2,
      visible: hasAnyRole(['company_admin', 'admin', 'platform_super_admin']),
      badge: 'Company',
    },
    {
      to: '/dashboard/sysadmin',
      label: t('nav.sysadminDashboard'),
      icon: HardDrive,
      visible: hasAnyRole(['it_admin', 'support', 'admin', 'company_admin', 'platform_super_admin']),
      badge: 'Ops',
    },
    {
      to: '/dashboard/executive',
      label: t('nav.executiveDashboard'),
      icon: PieChart,
      visible: hasAnyRole(['executive', 'admin', 'company_admin', 'platform_super_admin']),
      badge: 'SLA',
    },
    {
      to: '/dashboard/employee',
      label: t('nav.employeeDashboard'),
      icon: UserIcon,
      visible: true,
      badge: 'Portal',
    },
  ];

  const operationItems = [
    {
      to: '/inventory',
      label: t('nav.inventory'),
      icon: Server,
      visible: true,
    },
    {
      to: '/incidents',
      label: t('nav.incidents'),
      icon: ShieldAlert,
      visible: true,
    },
    {
      to: '/tickets',
      label: t('nav.helpdesk'),
      icon: LifeBuoy,
      visible: true,
    },
    {
      to: '/software',
      label: t('nav.software'),
      icon: Package,
      visible: true,
    },
  ];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-surface-100">
      {/* Sidebar for Desktop */}
      <aside className="hidden w-64 flex-col border-r border-surface-200 bg-white md:flex">
        {/* Brand Header */}
        <div className="flex h-16 items-center gap-2.5 border-b border-surface-200 px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-sm">
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-surface-900">{t('app.title')}</h1>
            <p className="text-[11px] font-medium text-surface-500">v1.0.0 &bull; Enterprise</p>
          </div>
        </div>

        {/* Navigation Section */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
          <div>
            <div className="mb-2 px-2 text-[10px] font-bold uppercase tracking-wider text-surface-400">
              {t('nav.dashboard')}
            </div>
            <nav className="space-y-1">
              {navItems
                .filter((item) => item.visible)
                .map((item) => {
                  const Icon = item.icon;
                  const isPrimary = user?.primary_dashboard && item.to.includes(user.primary_dashboard);
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={({ isActive }) =>
                        `flex items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold transition ${
                          isActive
                            ? 'bg-brand-50 text-brand-700 shadow-xs'
                            : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900'
                        }`
                      }
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className="h-4 w-4 shrink-0" />
                        <span>{item.label}</span>
                      </div>
                      {isPrimary && (
                        <span className="rounded bg-brand-100 px-1.5 py-0.5 text-[9px] font-bold text-brand-800">
                          {t('nav.myDashboard')}
                        </span>
                      )}
                    </NavLink>
                  );
                })}
            </nav>
          </div>

          <div>
            <div className="mb-2 px-2 text-[10px] font-bold uppercase tracking-wider text-surface-400">
              Amaliyotlar (Operations)
            </div>
            <nav className="space-y-1">
              {operationItems
                .filter((item) => item.visible)
                .map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={({ isActive }) =>
                        `flex items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold transition ${
                          isActive
                            ? 'bg-brand-50 text-brand-700 shadow-xs'
                            : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900'
                        }`
                      }
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className="h-4 w-4 shrink-0" />
                        <span>{item.label}</span>
                      </div>
                    </NavLink>
                  );
                })}
            </nav>
          </div>
        </div>

        {/* Footer User Info & Logout */}
        <div className="border-t border-surface-200 p-4">
          <div className="mb-3 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-100 text-xs font-bold text-brand-700 ring-1 ring-surface-300">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-surface-900">{user?.full_name}</p>
              <p className="truncate text-[11px] text-surface-500">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-surface-200 bg-surface-50 py-1.5 text-xs font-medium text-surface-700 hover:bg-red-50 hover:border-red-200 hover:text-red-700 transition"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span>{t('nav.logout')}</span>
          </button>
        </div>
      </aside>

      {/* Mobile Sidebar Overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div className="fixed inset-0 bg-black/40" onClick={() => setMobileMenuOpen(false)} />
          <div className="relative flex w-64 max-w-[80%] flex-col bg-white shadow-xl">
            <div className="flex h-16 items-center justify-between border-b border-surface-200 px-4">
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-brand-600" />
                <span className="font-bold text-surface-900">{t('app.title')}</span>
              </div>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="rounded-md p-1.5 text-surface-500 hover:bg-surface-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <div>
                <div className="mb-1.5 px-2 text-[10px] font-bold uppercase tracking-wider text-surface-400">
                  {t('nav.dashboard')}
                </div>
                <nav className="space-y-1">
                  {navItems
                    .filter((item) => item.visible)
                    .map((item) => {
                      const Icon = item.icon;
                      return (
                        <NavLink
                          key={item.to}
                          to={item.to}
                          onClick={() => setMobileMenuOpen(false)}
                          className={({ isActive }) =>
                            `flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-semibold ${
                              isActive
                                ? 'bg-brand-50 text-brand-700'
                                : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900'
                            }`
                          }
                        >
                          <Icon className="h-4 w-4" />
                          <span>{item.label}</span>
                        </NavLink>
                      );
                    })}
                </nav>
              </div>

              <div>
                <div className="mb-1.5 px-2 text-[10px] font-bold uppercase tracking-wider text-surface-400">
                  Amaliyotlar
                </div>
                <nav className="space-y-1">
                  {operationItems
                    .filter((item) => item.visible)
                    .map((item) => {
                      const Icon = item.icon;
                      return (
                        <NavLink
                          key={item.to}
                          to={item.to}
                          onClick={() => setMobileMenuOpen(false)}
                          className={({ isActive }) =>
                            `flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-semibold ${
                              isActive
                                ? 'bg-brand-50 text-brand-700'
                                : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900'
                            }`
                          }
                        >
                          <Icon className="h-4 w-4" />
                          <span>{item.label}</span>
                        </NavLink>
                      );
                    })}
                </nav>
              </div>
            </div>
            <div className="border-t border-surface-200 p-4">
              <button
                onClick={handleLogout}
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-surface-200 bg-surface-50 py-2 text-xs font-medium text-surface-700"
              >
                <LogOut className="h-4 w-4" />
                <span>{t('nav.logout')}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Viewport */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Header */}
        <header className="flex h-16 items-center justify-between border-b border-surface-200 bg-white px-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="rounded-lg p-2 text-surface-600 hover:bg-surface-100 md:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="hidden sm:flex items-center gap-2 text-xs text-surface-500">
              <LayoutDashboard className="h-4 w-4 text-surface-400" />
              <span>{t('nav.dashboard')}</span>
              <ChevronRight className="h-3.5 w-3.5 text-surface-300" />
              <span className="font-semibold text-surface-800">
                {user?.roles?.map((r) => r.name).join(', ') || 'User'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {user?.organization_id && (
              <div className="hidden lg:flex items-center gap-1.5 rounded-full bg-surface-100 px-3 py-1 text-xs font-medium text-surface-700">
                <Building2 className="h-3.5 w-3.5 text-surface-500" />
                <span>Org #{user.organization_id}</span>
              </div>
            )}
            <LanguageSwitcher />
          </div>
        </header>

        {/* Main Body */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
