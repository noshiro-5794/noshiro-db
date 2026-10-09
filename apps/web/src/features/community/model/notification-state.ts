import type { ApiPage, CommunityNotification } from '@/shared/api';

export type MarkNotificationsReadTarget = { kind: 'all' } | { kind: 'one'; notificationId: number };

export function markNotificationsReadInPage(
  page: ApiPage<CommunityNotification>,
  target: MarkNotificationsReadTarget,
  readAt: string,
): ApiPage<CommunityNotification> {
  const results = page.results.map((notification) => {
    const shouldMark = target.kind === 'all' || notification.id === target.notificationId;
    if (!shouldMark || notification.is_read) return notification;

    return { ...notification, is_read: true, read_at: notification.read_at ?? readAt };
  });

  const changed = results.some((notification, index) => notification !== page.results[index]);
  return changed ? { ...page, results } : page;
}

export function wasNotificationUnread(
  pages: Array<ApiPage<CommunityNotification> | undefined>,
  notificationId: number,
) {
  return pages.some((page) =>
    page?.results.some((notification) => notification.id === notificationId && !notification.is_read),
  );
}

export function nextUnreadCount(currentCount: number, target: MarkNotificationsReadTarget, targetWasUnread: boolean) {
  if (target.kind === 'all') return 0;
  return targetWasUnread ? Math.max(0, currentCount - 1) : currentCount;
}
