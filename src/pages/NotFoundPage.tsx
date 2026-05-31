import { Link } from 'react-router-dom';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';
import { EmptyState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

export function NotFoundPage() {
  const { t } = useI18n();

  return (
    <Page title={t('notFound.title')} description={t('notFound.description')}>
      <EmptyState
        title={t('notFound.stateTitle')}
        description={t('notFound.stateDescription')}
        action={
          <Link className="button button-primary" to={routes.home}>
            {t('notFound.action')}
          </Link>
        }
      />
    </Page>
  );
}
