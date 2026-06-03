import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { Bell, CheckCheck } from 'lucide-react';
import { communityMutations, communityQueries, communityQueryKeys } from '@/features/community/community-queries';
import { notificationHref, notificationMessage } from '@/features/community/notification-utils';
import { useI18n } from '@/features/i18n/use-i18n';
import type { CommunityNotification } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 24;

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

export function NotificationsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
  const notificationsQuery = useQuery(communityQueries.notifications({ page: currentPage, page_size: pageSize }));
  const markAllReadMutation = useMutation({
    ...communityMutations.markAllNotificationsRead(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: communityQueryKeys.notifications() });
    },
  });
  const markReadMutation = useMutation({
    ...communityMutations.markNotificationRead(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: communityQueryKeys.notifications() });
    },
  });
  const notifications = notificationsQuery.data?.results ?? [];
  const totalPages = Math.max(1, Math.ceil((notificationsQuery.data?.count ?? 0) / pageSize));

  function goToPage(page: number) {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(page));
    setSearchParams(next);
  }

  function markReadIfNeeded(notification: CommunityNotification) {
    if (!notification.is_read && !markReadMutation.isPending) {
      markReadMutation.mutate(notification.id);
    }
  }

  return (
    <Page
      title={t('community.notificationsTitle')}
      eyebrow={t('nav.groupWorkspace')}
      description={t('community.notificationsDescription')}
      actions={(
        <Button disabled={markAllReadMutation.isPending || notifications.length === 0} type="button" variant="secondary" onClick={() => markAllReadMutation.mutate()}>
          <CheckCheck className="size-4" /> {t('community.markAllRead')}
        </Button>
      )}
    >
      {notificationsQuery.isLoading ? <LoadingState title={t('community.loadingNotifications')} /> : null}
      {notificationsQuery.isError ? <ErrorState title={t('community.notificationsErrorTitle')} description={t('community.notificationsErrorBody')} /> : null}
      {!notificationsQuery.isLoading && !notificationsQuery.isError && notifications.length === 0 ? (
        <EmptyState title={t('community.noNotificationsTitle')} description={t('community.noNotificationsBody')} />
      ) : null}
      <div className="community-list">
        {notifications.map((notification) => {
          const href = notificationHref(notification);
          return (
            <article className={`community-list-item ${notification.is_read ? '' : 'is-unread'}`} key={notification.id}>
              <div className="grid grid-cols-[40px_minmax(0,1fr)] gap-3">
                <span className="grid size-10 place-items-center rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent-strong)]">
                  <Bell className="size-4" />
                </span>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    {notification.actor?.id ? (
                      <Link className="font-semibold text-neutral-950 transition hover:text-[var(--color-accent-strong)] dark:text-white" to={routes.userProfile(notification.actor.id)}>
                        {notification.actor.nickname || t('common.anonymous')}
                      </Link>
                    ) : (
                      <span className="font-semibold text-neutral-950 dark:text-white">{t('common.system')}</span>
                    )}
                    <span className="text-neutral-400">{formatDate(notification.created_at)}</span>
                    {!notification.is_read ? <span className="size-2 rounded-full bg-[var(--color-accent)]" aria-label={t('community.unread')} /> : null}
                  </div>
                  <p className="mt-1 text-sm leading-6 text-neutral-600 dark:text-neutral-300">
                    {notificationMessage(t, notification)}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {href ? (
                      <Button asChild size="sm" type="button" variant="secondary">
                        <Link to={href} onClick={() => markReadIfNeeded(notification)}>{t('community.openTarget')}</Link>
                      </Button>
                    ) : null}
                    {!notification.is_read ? (
                      <Button disabled={markReadMutation.isPending} size="sm" type="button" variant="ghost" onClick={() => markReadMutation.mutate(notification.id)}>
                        <CheckCheck className="size-4" /> {t('community.markRead')}
                      </Button>
                    ) : null}
                  </div>
                </div>
              </div>
            </article>
          );
        })}
      </div>
      <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
    </Page>
  );
}
