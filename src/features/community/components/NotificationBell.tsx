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
          className="workspace-tool-button relative"
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
      <PopoverContent align="end" className="w-[min(23rem,calc(100vw-2rem))] p-0" side="top">
        <div className="flex items-center justify-between gap-3 px-4 pb-3 pt-4">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-[var(--color-text)]">{t('community.recentNotifications')}</h2>
            <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">{t('community.notificationsPreviewDescription')}</p>
          </div>
          {unreadNotifications > 0 ? <Badge>{unreadNotifications > 99 ? '99+' : unreadNotifications}</Badge> : null}
        </div>
        <div className="max-h-96 overflow-y-auto px-2 pb-2">
          {notificationPreviewQuery.isLoading ? <LoadingState title={t('community.loadingNotifications')} /> : null}
          {!notificationPreviewQuery.isLoading && notificationPreview.length === 0 ? (
            <div className="px-2 py-3">
              <EmptyState title={t('community.noNotificationsTitle')} description={t('community.noNotificationsBody')} />
            </div>
          ) : null}
          {notificationPreview.map((notification) => {
            const href = notificationHref(notification) ?? routes.notifications;
            return (
              <Link
                className={[
                  'group relative grid gap-1 rounded-xl px-3 py-2.5 text-sm transition hover:bg-[var(--color-surface-muted)]',
                  notification.is_read ? '' : 'bg-[color-mix(in_srgb,var(--color-accent-soft)_52%,var(--color-surface-muted))]',
                ].join(' ')}
                key={notification.id}
                to={href}
                onClick={() => markNotificationReadIfNeeded(notification.id, notification.is_read)}
              >
                {!notification.is_read ? <span className="absolute left-1.5 top-3 size-1.5 rounded-full bg-[var(--color-accent)]" /> : null}
                <span className="flex min-w-0 items-center gap-2">
                  <span className="truncate font-semibold text-[var(--color-text)]">
                    {notification.actor?.nickname || t('common.system')}
                  </span>
                </span>
                <span className="line-clamp-2 text-[var(--color-text-muted)]">{notificationMessage(t, notification)}</span>
                <span className="text-xs text-neutral-400">{formatNotificationDate(notification.created_at)}</span>
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
