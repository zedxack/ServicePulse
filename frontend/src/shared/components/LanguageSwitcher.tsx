import React from 'react';
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';

export const LanguageSwitcher: React.FC<{ className?: string }> = ({ className = '' }) => {
  const { i18n } = useTranslation();

  const languages = [
    { code: 'uz', label: "O'zbek" },
    { code: 'ru', label: 'Русский' },
    { code: 'en', label: 'English' },
  ];

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const lang = e.target.value;
    i18n.changeLanguage(lang);
    localStorage.setItem('i18nextLng', lang);
  };

  const currentLang = i18n.language ? i18n.language.split('-')[0] : 'uz';

  return (
    <div className={`flex items-center gap-1.5 rounded-lg border border-surface-200 bg-white px-2 py-1 text-xs text-surface-700 shadow-sm ${className}`}>
      <Globe className="h-3.5 w-3.5 text-surface-500" />
      <select
        value={currentLang}
        onChange={handleLanguageChange}
        className="bg-transparent font-medium outline-none cursor-pointer text-surface-800"
        aria-label="Language selector"
      >
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.label}
          </option>
        ))}
      </select>
    </div>
  );
};
