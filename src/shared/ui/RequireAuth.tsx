import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/features/auth/use-auth';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';
import { LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

export function RequireAuth({ adminOnly = false, children }: { adminOnly?: boolean; children: ReactNode }) {
  const auth = useAuth();
  const { t } = useI18n();
  const location = useLocation();

  if (auth.status === 'checking') {
    return (
      <Page title="Noshiro DB" description={t('auth.checking')}>
        <LoadingState title={t('auth.checking')} />
      </Page>
    );
  }

  if (!auth.isAuthenticated) {
    return <Navigate replace state={{ returnTo: `${location.pathname}${location.search}${location.hash}` }} to={routes.login} />;
  }

  if (adminOnly && auth.role !== 'admin') {
    return <Navigate replace to={routes.home} />;
  }

  return children;
}
