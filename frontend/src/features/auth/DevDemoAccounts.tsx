import React from 'react';
import { useTranslation } from 'react-i18next';
import { ShieldCheck } from 'lucide-react';

interface DevDemoAccountsProps {
  onSelect: (email: string, pass: string) => void;
}

export const DevDemoAccounts: React.FC<DevDemoAccountsProps> = ({ onSelect }) => {
  const { t } = useTranslation();

  return (
    <div className="mt-8 border-t border-surface-200 pt-5" data-testid="dev-demo-accounts">
      <div className="mb-3 flex items-center justify-between text-xs font-semibold text-surface-600">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5 text-brand-600" />
          <span>{t('auth.demoAccounts')}</span>
        </div>
        <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[9px] font-bold text-amber-800 uppercase tracking-wide">
          DEV ONLY
        </span>
      </div>
      <div className="grid grid-cols-1 gap-1.5 text-xs">
        <button
          type="button"
          onClick={() => onSelect('admin@servicepulse.uz', 'AdminPass2026!')}
          className="flex items-center justify-between rounded-md border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-left font-medium text-surface-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
        >
          <span>{t('auth.superAdmin')}</span>
          <span className="font-mono text-[10px] text-surface-500">admin@servicepulse.uz</span>
        </button>
        <button
          type="button"
          onClick={() => onSelect('company_admin@servicepulse.uz', 'CompanyAdminPass2026!')}
          className="flex items-center justify-between rounded-md border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-left font-medium text-surface-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
        >
          <span>{t('auth.companyAdmin')}</span>
          <span className="font-mono text-[10px] text-surface-500">company_admin@servicepulse.uz</span>
        </button>
        <button
          type="button"
          onClick={() => onSelect('support@servicepulse.uz', 'SupportPass2026!')}
          className="flex items-center justify-between rounded-md border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-left font-medium text-surface-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
        >
          <span>{t('auth.sysAdmin')}</span>
          <span className="font-mono text-[10px] text-surface-500">support@servicepulse.uz</span>
        </button>
        <button
          type="button"
          onClick={() => onSelect('executive@servicepulse.uz', 'ExecutivePass2026!')}
          className="flex items-center justify-between rounded-md border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-left font-medium text-surface-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
        >
          <span>{t('auth.executive')}</span>
          <span className="font-mono text-[10px] text-surface-500">executive@servicepulse.uz</span>
        </button>
        <button
          type="button"
          onClick={() => onSelect('employee@servicepulse.uz', 'EmployeePass2026!')}
          className="flex items-center justify-between rounded-md border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-left font-medium text-surface-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
        >
          <span>{t('auth.employee')}</span>
          <span className="font-mono text-[10px] text-surface-500">employee@servicepulse.uz</span>
        </button>
      </div>
    </div>
  );
};

export default DevDemoAccounts;
