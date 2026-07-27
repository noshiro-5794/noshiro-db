import type { ReactNode } from 'react';
import { Navigate, useLocation } from '@/shared/routing/navigation';
import { useAuth } from '@/entities/session';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

export function RequireAuth({ adminOnly = false, children }: { adminOnly?: boolean; children: ReactNode }) {
  const auth = useAuth();
  const { t } = useI18n();
  const location = useLocation();

  if (auth.status === 'checking') {
    return (
      <Page title="Noshiro DB">
        <LoadingState title={t('auth.checking')} />
      </Page>
    );
  }

  if (!auth.isAuthenticated) {
    return (
      <Navigate
        replace
        state={{ returnTo: `${location.pathname}${location.search}${location.hash}` }}
        to={routes.login}
      />
    );
  }

  if (adminOnly && auth.role !== 'admin') {
    return <Navigate replace to={routes.home} />;
  }

  return children;
}
