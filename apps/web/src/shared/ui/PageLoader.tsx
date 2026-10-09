import { useI18n } from '@/shared/i18n';

export function PageLoader() {
  const { t } = useI18n();

  return (
    <div className="grid min-h-[50vh] place-items-center bg-[var(--ui-bg-canvas)] text-[var(--ui-text)]">
      <span
        className="size-5 animate-spin rounded-full border-2 border-[var(--ui-border)] border-t-[var(--ui-text-muted)]"
        aria-label={t('common.loading')}
        role="status"
      />
    </div>
  );
}
