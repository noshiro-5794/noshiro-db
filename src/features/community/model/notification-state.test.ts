import { describe, expect, it } from 'vitest';
import type { ApiPage, CommunityNotification } from '@/shared/api';
import { markNotificationsReadInPage, nextUnreadCount, wasNotificationUnread } from './notification-state';

function notification(id: number, isRead = false): CommunityNotification {
  return {
    id,
    notification_type: 'comment_created',
    actor: null,
    target: null,
    metadata: {},
    is_read: isRead,
    read_at: null,
    created_at: '2026-07-29T00:00:00Z',
  };
}

function page(results: CommunityNotification[]): ApiPage<CommunityNotification> {
  return { count: results.length, next: null, previous: null, results };
}

describe('notification optimistic state', () => {
  it('marks only the requested unread notification without mutating the cached page', () => {
    const cachedPage = page([notification(1), notification(2, true)]);
    const nextPage = markNotificationsReadInPage(
      cachedPage,
      { kind: 'one', notificationId: 1 },
      '2026-07-29T01:00:00Z',
    );

    expect(nextPage).not.toBe(cachedPage);
    expect(cachedPage.results[0]?.is_read).toBe(false);
    expect(nextPage.results[0]).toMatchObject({ is_read: true, read_at: '2026-07-29T01:00:00Z' });
    expect(nextPage.results[1]).toBe(cachedPage.results[1]);
  });

  it('marks every unread notification and preserves an unchanged page identity', () => {
    const unreadPage = page([notification(1), notification(2)]);
    const readPage = page([notification(3, true)]);

    expect(markNotificationsReadInPage(unreadPage, { kind: 'all' }, 'now').results).toEqual([
      expect.objectContaining({ id: 1, is_read: true, read_at: 'now' }),
      expect.objectContaining({ id: 2, is_read: true, read_at: 'now' }),
    ]);
    expect(markNotificationsReadInPage(readPage, { kind: 'all' }, 'now')).toBe(readPage);
  });

  it('updates the unread counter only when the target was unread', () => {
    const pages = [page([notification(1), notification(2, true)])];

    expect(wasNotificationUnread(pages, 1)).toBe(true);
    expect(wasNotificationUnread(pages, 2)).toBe(false);
    expect(nextUnreadCount(4, { kind: 'one', notificationId: 1 }, true)).toBe(3);
    expect(nextUnreadCount(4, { kind: 'one', notificationId: 2 }, false)).toBe(4);
    expect(nextUnreadCount(4, { kind: 'all' }, true)).toBe(0);
  });
});
