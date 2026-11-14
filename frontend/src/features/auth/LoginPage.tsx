import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Activity, AlertCircle, ArrowRight, Lock, Mail, ShieldCheck } from 'lucide-react';
import { useAuth } from './AuthContext';
import { LanguageSwitcher } from '../../shared/components/LanguageSwitcher';

export const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const user = await login({ email, password });
      // Redirect based on backend computed primary_dashboard
      const dashboardTarget = user.primary_dashboard || 'employee';
      navigate(`/dashboard/${dashboardTarget}`, { replace: true });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const detail = axiosErr.response?.data?.detail;
      setError(detail || t('auth.invalidCredentials'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const setDemoCredentials = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div className="flex min-h-screen flex-col bg-surface-50 text-surface-900">
      {/* Top Navbar */}
      <header className="flex items-center justify-between border-b border-surface-200 bg-white px-6 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-sm">
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-surface-900">{t('app.title')}</h1>
            <p className="text-xs text-surface-500">{t('app.subtitle')}</p>
          </div>
        </div>
        <LanguageSwitcher />
      </header>

      {/* Main Login Area */}
      <main className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-md space-y-6">
          <div className="rounded-2xl border border-surface-200 bg-white p-8 shadow-sm">
            <div className="mb-6 text-center">
              <h2 className="text-xl font-bold tracking-tight text-surface-900">{t('auth.loginTitle')}</h2>
              <p className="mt-1 text-sm text-surface-500">{t('auth.loginSubtitle')}</p>
            </div>

            {error && (
              <div className="mb-5 flex items-center gap-2.5 rounded-lg border border-red-200 bg-red-50 p-3.5 text-xs text-red-700">
                <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-semibold text-surface-700">
                  {t('auth.emailLabel')}
                </label>
                <div className="relative">
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
                    <Mail className="h-4 w-4" />
                  </div>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="nom@servicepulse.uz"
                    className="w-full rounded-lg border border-surface-300 bg-white py-2.5 pl-9 pr-3 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs font-semibold text-surface-700">
                  {t('auth.passwordLabel')}
                </label>
                <div className="relative">
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
                    <Lock className="h-4 w-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full rounded-lg border border-surface-300 bg-white py-2.5 pl-9 pr-3 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 disabled:opacity-60"
              >
                {isSubmitting ? (
                  <span>{t('auth.loggingIn')}</span>
                ) : (
                  <>
                    <span>{t('auth.loginButton')}</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>

            {/* Quick Demo Accounts Selection */}
            <div className="mt-8 border-t border-surface-200 pt-5">
              <div className="mb-3 flex items-center gap-1.5 text-xs font-semibold text-surface-600">
                <ShieldCheck className="h-3.5 w-3.5 text-brand-600" />
                <span>{t('auth.demoAccounts')}</span>
              </div>
              <div className="grid grid-cols-1 gap-1.5 text-xs">
                <button
                  type="button"
                  onClick={() => setDemoCredentials('admin@servicepulse.uz', 'AdminPass2026!')}
                  className="flex items-center justify-between rounded-md border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-left font-medium text-surface-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                >
                  <span>{t('auth.superAdmin')}</span>
                  <span className="font-mono text-[10px] text-surface-500">admin@servicepulse.uz</span>
                </button>
                <button
                  type="button"
                  onClick={() => setDemoCredentials('company_admin@servicepulse.uz', 'CompanyAdminPass2026!')}
                  className="flex items-center justify-between rounded-md border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-left font-medium text-surface-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                >
                  <span>{t('auth.companyAdmin')}</span>
                  <span className="font-mono text-[10px] text-surface-500">company_admin@servicepulse.uz</span>
                </button>
                <button
                  type="button"
                  onClick={() => setDemoCredentials('support@servicepulse.uz', 'SupportPass2026!')}
                  className="flex items-center justify-between rounded-md border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-left font-medium text-surface-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                >
                  <span>{t('auth.sysAdmin')}</span>
                  <span className="font-mono text-[10px] text-surface-500">support@servicepulse.uz</span>
                </button>
                <button
                  type="button"
                  onClick={() => setDemoCredentials('executive@servicepulse.uz', 'ExecutivePass2026!')}
                  className="flex items-center justify-between rounded-md border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-left font-medium text-surface-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                >
                  <span>{t('auth.executive')}</span>
                  <span className="font-mono text-[10px] text-surface-500">executive@servicepulse.uz</span>
                </button>
                <button
                  type="button"
                  onClick={() => setDemoCredentials('employee@servicepulse.uz', 'EmployeePass2026!')}
                  className="flex items-center justify-between rounded-md border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-left font-medium text-surface-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                >
                  <span>{t('auth.employee')}</span>
                  <span className="font-mono text-[10px] text-surface-500">employee@servicepulse.uz</span>
                </button>
              </div>
            </div>
          </div>

          <p className="text-center text-xs text-surface-400">
            {t('app.tagline')} &bull; Muhammadyusuf Usmonov
          </p>
        </div>
      </main>
    </div>
  );
};
