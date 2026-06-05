import { useI18n } from '@/features/i18n/use-i18n';

export function PageLoader() {
  const { t } = useI18n();

  return (
    <div className="grid min-h-screen place-items-center bg-[var(--color-bg)] text-[var(--color-text)]">
      <span
        className="size-5 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-text-muted)]"
        aria-label={t('common.loading')}
        role="status"
      />
    </div>
  );
}
