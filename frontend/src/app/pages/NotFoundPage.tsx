import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, FileQuestion } from 'lucide-react';
import { useAuth } from '../../features/auth/AuthContext';

export const NotFoundPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const targetDashboard = user?.primary_dashboard ? `/dashboard/${user.primary_dashboard}` : '/login';

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface-50 p-6 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface-200 text-surface-600 shadow-xs">
        <FileQuestion className="h-8 w-8" />
      </div>
      <h1 className="mt-6 text-2xl font-bold tracking-tight text-surface-900">{t('common.pageNotFound')}</h1>
      <p className="mt-2 max-w-sm text-sm text-surface-500">{t('common.pageNotFoundDesc')}</p>
      <Link
        to={targetDashboard}
        className="mt-6 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-brand-700 transition"
      >
        <ArrowLeft className="h-4 w-4" />
        <span>{t('common.backToHome')}</span>
      </Link>
    </div>
  );
};
