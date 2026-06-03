import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bell } from 'lucide-react';
import { communityMutations, communityQueries, communityQueryKeys } from '@/features/community/community-queries';
import { notificationHref, notificationMessage } from '@/features/community/notification-utils';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState, LoadingState } from '@/shared/ui/FeedbackState';
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/ui/Popover';

function formatNotificationDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

export function NotificationBell() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const unreadNotificationsQuery = useQuery({
    ...communityQueries.unreadCount(),
    refetchInterval: 60_000,
  });
  const notificationPreviewQuery = useQuery({
    ...communityQueries.notifications({ page: 1, page_size: 5 }),
    refetchInterval: 60_000,
  });
  const markReadMutation = useMutation({
    ...communityMutations.markNotificationRead(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: communityQueryKeys.notifications() });
    },
  });
  const unreadNotifications = unreadNotificationsQuery.data?.unread_count ?? 0;
  const notificationPreview = notificationPreviewQuery.data?.results ?? [];

  function markNotificationReadIfNeeded(notificationId: number, isRead?: boolean) {
    if (!isRead && !markReadMutation.isPending) {
      markReadMutation.mutate(notificationId);
    }
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          aria-label={t('nav.notifications')}
          className="relative grid size-10 place-items-center rounded-xl border border-neutral-200 bg-neutral-50 text-neutral-500 transition hover:border-[var(--color-accent-border)] hover:text-neutral-950 dark:border-neutral-800 dark:bg-neutral-900/70 dark:text-neutral-400 dark:hover:text-white"
          type="button"
        >
          <Bell className="size-4" />
          {unreadNotifications > 0 ? (
            <span className="absolute -right-1 -top-1 grid min-w-5 place-items-center rounded-full bg-[var(--color-accent)] px-1 text-[10px] font-bold leading-5 text-[var(--color-accent-contrast)] ring-2 ring-[var(--color-bg)]">
              {unreadNotifications > 99 ? '99+' : unreadNotifications}
            </span>
          ) : null}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[min(22rem,calc(100vw-1.5rem))] p-0">
        <div className="flex items-center justify-between gap-3 border-b border-neutral-200 p-3 dark:border-neutral-800">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-neutral-950 dark:text-white">{t('community.recentNotifications')}</h2>
            <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">{t('community.notificationsPreviewDescription')}</p>
          </div>
          {unreadNotifications > 0 ? <Badge>{unreadNotifications > 99 ? '99+' : unreadNotifications}</Badge> : null}
        </div>
        <div className="max-h-96 overflow-y-auto">
          {notificationPreviewQuery.isLoading ? <LoadingState title={t('community.loadingNotifications')} /> : null}
          {!notificationPreviewQuery.isLoading && notificationPreview.length === 0 ? (
            <div className="p-3">
              <EmptyState title={t('community.noNotificationsTitle')} description={t('community.noNotificationsBody')} />
            </div>
          ) : null}
          {notificationPreview.map((notification) => {
            const href = notificationHref(notification) ?? routes.notifications;
            return (
              <Link
                className={[
                  'grid gap-1 border-b border-neutral-100 px-3 py-3 text-sm transition last:border-b-0 hover:bg-neutral-50 dark:border-neutral-900 dark:hover:bg-neutral-900/70',
                  notification.is_read ? '' : 'bg-[var(--color-accent-soft)]/40',
                ].join(' ')}
                key={notification.id}
                to={href}
                onClick={() => markNotificationReadIfNeeded(notification.id, notification.is_read)}
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span className="truncate font-semibold text-neutral-950 dark:text-white">
                    {notification.actor?.nickname || t('common.system')}
                  </span>
                  {!notification.is_read ? <span className="size-1.5 rounded-full bg-[var(--color-accent)]" /> : null}
                </span>
                <span className="line-clamp-2 text-neutral-600 dark:text-neutral-300">{notificationMessage(t, notification)}</span>
                <span className="text-xs text-neutral-400">{formatNotificationDate(notification.created_at)}</span>
              </Link>
            );
          })}
        </div>
        <div className="border-t border-neutral-200 p-3 dark:border-neutral-800">
          <Button asChild className="w-full" size="sm" type="button" variant="secondary">
            <Link to={routes.notifications}>{t('community.viewAllNotifications')}</Link>
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
