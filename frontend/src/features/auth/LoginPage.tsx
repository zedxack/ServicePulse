import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Activity, AlertCircle, ArrowRight, Eye, EyeOff, Lock, Mail } from 'lucide-react';
import { useAuth } from './AuthContext';
import { LanguageSwitcher } from '../../shared/components/LanguageSwitcher';
import { JoinOrganizationForm } from './JoinOrganizationForm';
import { RegisterOrganizationForm } from './RegisterOrganizationForm';

type AuthMode = 'login' | 'join' | 'register_org';

export const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<AuthMode>('login');

  // Login form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const user = await login({ email, password });
      const dashboardTarget = user.primary_dashboard || 'employee';
      navigate(`/dashboard/${dashboardTarget}`, { replace: true });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const detail = axiosErr.response?.data?.detail;
      setError(detail || t('auth.invalidCredentials', 'Incorrect email or password'));
    } finally {
      setIsSubmitting(false);
    }
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
            <h1 className="text-base font-bold tracking-tight text-surface-900">{t('app.title', 'ServicePulse')}</h1>
            <p className="text-xs text-surface-500">{t('app.subtitle', 'Hybrid RMM & ITSM Platform')}</p>
          </div>
        </div>
        <LanguageSwitcher />
      </header>

      {/* Main Container */}
      <main className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-lg space-y-6">
          <div className="rounded-2xl border border-surface-200 bg-white p-8 shadow-sm">
            {/* Header Titles */}
            <div className="mb-6 text-center">
              <h2 className="text-xl font-bold tracking-tight text-surface-900">
                {mode === 'login' && t('auth.loginTitle', 'Sign in to ServicePulse')}
                {mode === 'join' && t('auth.joinTitle', 'Join Existing Organization')}
                {mode === 'register_org' && t('auth.registerOrgTitle', 'Register New Organization')}
              </h2>
              <p className="mt-1 text-xs text-surface-500">
                {mode === 'login' && t('auth.loginSubtitle', 'Enter your corporate credentials to continue')}
                {mode === 'join' && t('auth.joinSubtitle', 'Use your invitation code to activate your account')}
                {mode === 'register_org' && t('auth.registerOrgSubtitle', 'Apply for a new tenant space for your institution')}
              </p>
            </div>

            {/* Mode Navigation Tabs */}
            <div className="mb-6 flex rounded-lg bg-surface-100 p-1 text-xs font-semibold">
              <button
                type="button"
                data-testid="tab-login"
                onClick={() => {
                  setMode('login');
                  setError(null);
                }}
                className={`flex-1 rounded-md py-2 transition-all ${
                  mode === 'login'
                    ? 'bg-white text-surface-900 shadow-sm'
                    : 'text-surface-600 hover:text-surface-900'
                }`}
              >
                {t('auth.tabSignIn', 'Sign In')}
              </button>
              <button
                type="button"
                data-testid="tab-join"
                onClick={() => {
                  setMode('join');
                  setError(null);
                }}
                className={`flex-1 rounded-md py-2 transition-all ${
                  mode === 'join'
                    ? 'bg-white text-surface-900 shadow-sm'
                    : 'text-surface-600 hover:text-surface-900'
                }`}
              >
                {t('auth.tabJoinOrg', 'Join with Invite')}
              </button>
              <button
                type="button"
                data-testid="tab-register-org"
                onClick={() => {
                  setMode('register_org');
                  setError(null);
                }}
                className={`flex-1 rounded-md py-2 transition-all ${
                  mode === 'register_org'
                    ? 'bg-white text-surface-900 shadow-sm'
                    : 'text-surface-600 hover:text-surface-900'
                }`}
              >
                {t('auth.tabNewOrg', 'New Organization')}
              </button>
            </div>

            {/* Login Mode */}
            {mode === 'login' && (
              <div>
                {error && (
                  <div className="mb-5 flex items-center gap-2.5 rounded-lg border border-red-200 bg-red-50 p-3.5 text-xs text-red-700">
                    <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
                    <span>{error}</span>
                  </div>
                )}

                <form onSubmit={handleLoginSubmit} className="space-y-4">
                  <div>
                    <label className="mb-1 block text-xs font-semibold text-surface-700">
                      {t('auth.emailLabel', 'Corporate Email')}
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
                      {t('auth.passwordLabel', 'Password')}
                    </label>
                    <div className="relative">
                      <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
                        <Lock className="h-4 w-4" />
                      </div>
                      <input
                        type={showPassword ? 'text' : 'password'}
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••••••"
                        className="w-full rounded-lg border border-surface-300 bg-white py-2.5 pl-9 pr-10 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute inset-y-0 right-0 flex items-center pr-3 text-surface-400 hover:text-surface-600"
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    data-testid="login-submit-btn"
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 disabled:opacity-60"
                  >
                    {isSubmitting ? (
                      <span>{t('auth.loggingIn', 'Signing In...')}</span>
                    ) : (
                      <>
                        <span>{t('auth.loginButton', 'Sign In')}</span>
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </button>
                </form>
              </div>
            )}

            {/* Join Existing Organization Mode */}
            {mode === 'join' && (
              <JoinOrganizationForm onSwitchToLogin={() => setMode('login')} />
            )}

            {/* Register New Organization Mode */}
            {mode === 'register_org' && (
              <RegisterOrganizationForm onSwitchToLogin={() => setMode('login')} />
            )}
          </div>

          <p className="text-center text-xs text-surface-400">
            {t('app.tagline', 'Enterprise Hybrid RMM & ITSM')} &bull; Muhammadyusuf Usmonov (AT-Servis BMI)
          </p>
        </div>
      </main>
    </div>
  );
};
