import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/features/auth/use-auth';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';
import { LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

export function RequireAuth({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const { t } = useI18n();

  if (auth.status === 'checking') {
    return (
      <Page title="Noshiro DB" description={t('auth.checking')}>
        <LoadingState title={t('auth.checking')} />
      </Page>
    );
  }

  if (!auth.isAuthenticated) {
    return <Navigate replace to={routes.login} />;
  }

  return children;
}
