import { useI18n } from '@/features/i18n/use-i18n';

export function AuthEntry() {
  const { t } = useI18n();

  return (
    <div className="auth-entry">
      <div>
        <h2>{t('home.guestTitle')}</h2>
        <p>{t('home.guestBody')}</p>
      </div>
      <div className="auth-actions">
        <button className="button button-primary" type="button">
          {t('auth.login')}
        </button>
        <button className="button button-secondary" type="button">
          {t('auth.register')}
        </button>
      </div>
    </div>
  );
}
