import { useI18n } from '@/features/i18n/use-i18n';
import { Page } from '@/shared/ui/Page';

export function CalendarPage() {
  const { t } = useI18n();

  return <Page title={t('calendar.title')} />;
}
