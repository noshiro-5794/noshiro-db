import { formatDate } from '@/shared/lib/date';
import { useQuery } from '@tanstack/react-query';
import { getRouteApi, Link } from '@tanstack/react-router';
import { Bell, CheckCheck } from 'lucide-react';
import { communityQueries } from '@/entities/community';
import { useMarkNotificationsReadMutation } from '@/features/community';
import { notificationHref, notificationMessage } from '@/entities/community';
import { useI18n } from '@/shared/i18n';
import type { CommunityNotification } from '@/shared/api';
import { resolvedRouteHref } from '@/shared/routing/resolved-href';
import { Button } from '@/shared/ui/Button';
import { ListSurface, ResultsMeta, ResultsState, type ResultsStatus } from '@/shared/ui/DataView';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 24;
const notificationsRoute = getRouteApi('/notifications');

export function NotificationsPage() {
  const { t } = useI18n();
  const navigate = notificationsRoute.useNavigate();
  const { page: currentPage = 1 } = notificationsRoute.useSearch();
  const notificationsQuery = useQuery(communityQueries.notifications({ page: currentPage, page_size: pageSize }));
  const markReadMutation = useMarkNotificationsReadMutation();
  const notifications = notificationsQuery.data?.results ?? [];
  const totalPages = Math.max(1, Math.ceil((notificationsQuery.data?.count ?? 0) / pageSize));
  const resultsStatus: ResultsStatus =
    notificationsQuery.data === undefined && notificationsQuery.isLoading
      ? 'loading'
      : notificationsQuery.data === undefined && notificationsQuery.isError
        ? 'error'
        : notifications.length === 0
          ? 'empty'
          : 'ready';

  function goToPage(page: number) {
    void navigate({ search: (current) => ({ ...current, page }) });
  }

  function markReadIfNeeded(notification: CommunityNotification) {
    if (!notification.is_read && !markReadMutation.isPending) {
      markReadMutation.mutate({ kind: 'one', notificationId: notification.id });
    }
  }

  return (
    <Page
      title={t('community.notificationsTitle')}
      eyebrow={t('nav.groupCommunity')}
      actions={
        <Button
          disabled={markReadMutation.isPending || notifications.length === 0}
          type="button"
          variant="secondary"
          onClick={() => {
            markReadMutation.mutate({ kind: 'all' });
          }}
        >
          <CheckCheck className="size-4" /> {t('community.markAllRead')}
        </Button>
      }
    >
      <div className="grid gap-4">
        <ResultsMeta
          count={notificationsQuery.data?.count}
          label={t('community.notificationsTitle')}
          pending={notificationsQuery.isFetching && !notificationsQuery.isLoading}
          pendingLabel={t('common.loading')}
        />
        <ResultsState
          emptyDescription={t('community.noNotificationsBody')}
          emptyTitle={t('community.noNotificationsTitle')}
          errorDescription={t('community.notificationsErrorBody')}
          errorTitle={t('community.notificationsErrorTitle')}
          loadingTitle={t('community.loadingNotifications')}
          status={resultsStatus}
        >
          <>
            <ListSurface>
              {notifications.map((notification) => {
                const href = notificationHref(notification);
                return (
                  <article
                    className="border-b border-border-subtle px-3 py-3 transition-colors last:border-b-0 hover:bg-muted data-[unread]:bg-[color-mix(in_srgb,var(--ui-accent-soft)_48%,var(--ui-bg-surface))] data-[unread]:shadow-[inset_2px_0_0_var(--ui-accent)] sm:px-4"
                    data-slot="notification-row"
                    data-unread={notification.is_read ? undefined : true}
                    key={notification.id}
                  >
                    <div className="grid grid-cols-[40px_minmax(0,1fr)] gap-3">
                      <span className="grid size-10 place-items-center rounded-full bg-[var(--ui-accent-soft)] text-[var(--ui-accent-text)]">
                        <Bell className="size-4" />
                      </span>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2 text-sm">
                          {notification.actor?.id ? (
                            <Link
                              className="font-semibold text-[var(--ui-text)] transition hover:text-[var(--ui-accent-text)]"
                              params={{ userId: String(notification.actor.id) }}
                              to="/users/$userId"
                            >
                              {notification.actor.nickname || t('common.anonymous')}
                            </Link>
                          ) : (
                            <span className="font-semibold text-[var(--ui-text)]">{t('common.system')}</span>
                          )}
                          <span className="text-[var(--ui-text-subtle)]">{formatDate(notification.created_at)}</span>
                          {!notification.is_read ? (
                            <span
                              aria-label={t('community.unread')}
                              className="size-2 rounded-full bg-[var(--ui-accent)]"
                            />
                          ) : null}
                        </div>
                        <p className="mt-1 text-sm leading-6 text-[var(--ui-text-muted)]">
                          {notificationMessage(t, notification)}
                        </p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {href ? (
                            <Button asChild size="sm" type="button" variant="secondary">
                              <Link
                                onClick={() => {
                                  markReadIfNeeded(notification);
                                }}
                                {...resolvedRouteHref(href)}
                              >
                                {t('community.openTarget')}
                              </Link>
                            </Button>
                          ) : null}
                          {!notification.is_read ? (
                            <Button
                              disabled={markReadMutation.isPending}
                              size="sm"
                              type="button"
                              variant="ghost"
                              onClick={() => {
                                markReadMutation.mutate({ kind: 'one', notificationId: notification.id });
                              }}
                            >
                              <CheckCheck className="size-4" /> {t('community.markRead')}
                            </Button>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })}
            </ListSurface>
            <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
          </>
        </ResultsState>
      </div>
    </Page>
  );
}
