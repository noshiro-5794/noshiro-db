import { formatDate as formatNotificationDate } from '@/shared/lib/date';
import { Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Bell } from 'lucide-react';
import { communityQueries } from '@/entities/community';
import { notificationHref, notificationMessage } from '@/entities/community';
import { useMarkNotificationsReadMutation } from '@/features/community';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/ui/Popover';

export function NotificationBell() {
  const { t } = useI18n();
  const unreadNotificationsQuery = useQuery({
    ...communityQueries.unreadCount(),
    refetchInterval: 60_000,
  });
  const notificationPreviewQuery = useQuery({
    ...communityQueries.notifications({ page_size: 5 }),
    refetchInterval: 60_000,
  });
  const markReadMutation = useMarkNotificationsReadMutation();
  const unreadNotifications = unreadNotificationsQuery.data?.unread_count ?? 0;
  const notificationPreview = notificationPreviewQuery.data?.results ?? [];

  function markNotificationReadIfNeeded(notificationId: number, isRead?: boolean) {
    if (!isRead) {
      markReadMutation.mutate({ kind: 'one', notificationId });
    }
  }

  return (
    <Popover>
      <PopoverTrigger
        render={
          <Button
            aria-label={t('nav.notifications')}
            className="relative"
            size="icon"
            tooltip={t('nav.notifications')}
            type="button"
            variant="ghost"
          />
        }
      >
        <Bell className="size-4" />
        {unreadNotifications > 0 ? (
          <span className="absolute -right-1 -top-1 grid min-w-5 place-items-center rounded-full bg-[var(--ui-accent-solid)] px-1 text-[10px] font-bold leading-5 text-[var(--ui-accent-solid-text)] ring-2 ring-[var(--ui-bg-canvas)]">
            {unreadNotifications > 99 ? '99+' : unreadNotifications}
          </span>
        ) : null}
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[min(23rem,calc(100vw-2rem))] p-0" side="top">
        <div className="flex items-center justify-between gap-3 px-4 pb-3 pt-4">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-[var(--ui-text)]">
              {t('community.recentNotifications')}
            </h2>
            <p className="mt-0.5 text-xs text-[var(--ui-text-muted)]">
              {t('community.notificationsPreviewDescription')}
            </p>
          </div>
          {unreadNotifications > 0 ? <Badge>{unreadNotifications > 99 ? '99+' : unreadNotifications}</Badge> : null}
        </div>
        <div className="max-h-96 overflow-y-auto px-2 pb-2">
          {notificationPreviewQuery.isLoading ? <LoadingState title={t('community.loadingNotifications')} /> : null}
          {notificationPreviewQuery.isError ? (
            <ErrorState
              title={t('community.notificationsErrorTitle')}
              description={t('community.notificationsErrorBody')}
            />
          ) : null}
          {!notificationPreviewQuery.isLoading &&
          !notificationPreviewQuery.isError &&
          notificationPreview.length === 0 ? (
            <div className="px-2 py-3">
              <EmptyState
                title={t('community.noNotificationsTitle')}
                description={t('community.noNotificationsBody')}
              />
            </div>
          ) : null}
          {notificationPreview.map((notification) => {
            const href = notificationHref(notification) ?? routes.notifications;
            return (
              <Link
                className={[
                  'group relative grid gap-1 rounded-md px-3 py-2.5 text-sm transition-colors hover:bg-[var(--ui-bg-subtle)]',
                  notification.is_read ? '' : 'bg-[color-mix(in_srgb,var(--ui-accent-soft)_52%,var(--ui-bg-subtle))]',
                ].join(' ')}
                key={notification.id}
                to={href}
                onClick={() => {
                  markNotificationReadIfNeeded(notification.id, notification.is_read);
                }}
              >
                {!notification.is_read ? (
                  <span className="absolute left-1.5 top-3 size-1.5 rounded-full bg-[var(--ui-accent)]" />
                ) : null}
                <span className="flex min-w-0 items-center gap-2">
                  <span className="truncate font-semibold text-[var(--ui-text)]">
                    {notification.actor?.nickname || t('common.system')}
                  </span>
                </span>
                <span className="line-clamp-2 text-[var(--ui-text-muted)]">{notificationMessage(t, notification)}</span>
                <span className="text-xs text-[var(--ui-text-subtle)]">
                  {formatNotificationDate(notification.created_at)}
                </span>
              </Link>
            );
          })}
        </div>
        <div className="px-2 pb-2">
          <Button asChild className="h-9 w-full" size="sm" type="button" variant="ghost">
            <Link to={routes.notifications}>{t('community.viewAllNotifications')}</Link>
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
