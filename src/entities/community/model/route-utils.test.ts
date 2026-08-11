import { describe, expect, it } from 'vitest';
import type { Activity, CommunityNotification } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { activityTargetHref } from './activity-target';
import { notificationHref } from './notification-utils';

function notification(overrides: Partial<CommunityNotification>): CommunityNotification {
  return {
    id: 1,
    notification_type: 'commented',
    actor: null,
    target: null,
    metadata: {},
    is_read: false,
    read_at: null,
    created_at: '2026-07-28T00:00:00Z',
    ...overrides,
  };
}

function activity(overrides: Partial<Activity>): Activity {
  return {
    id: 1,
    activity_type: 'post_created',
    created_at: '2026-07-28T00:00:00Z',
    ...overrides,
  };
}

describe('notificationHref', () => {
  it('links follow notifications to the actor without trusting string metadata IDs', () => {
    expect(notificationHref(notification({ notification_type: 'followed', metadata: { actor_id: 42 } }))).toBe(
      routes.userProfile(42),
    );
    expect(notificationHref(notification({ notification_type: 'followed', metadata: { actor_id: '42' } }))).toBeNull();
  });

  it('routes comments to their concrete parent and adds an encoded anchor', () => {
    expect(
      notificationHref(
        notification({
          target: { type: 'comment', id: 8, post: { type: 'post', id: 21 } },
        }),
      ),
    ).toBe(`${routes.communityPost(21)}#comment-8`);
  });

  it('uses safe local fallbacks when a target is incomplete or unknown', () => {
    expect(notificationHref(notification({ target: { type: 'collection', id: 5 } }))).toBe(routes.collections);
    expect(notificationHref(notification({ target: { type: 'future-target', id: 5 } }))).toBeNull();
  });
});

describe('activityTargetHref', () => {
  it('routes comment activity to the parent content and anchor', () => {
    expect(
      activityTargetHref(
        activity({
          activity_type: 'comment_created',
          post: {
            id: 9,
            content: 'post',
            visibility: 'public',
            is_spoiler: false,
            is_nsfw: false,
          },
          comment: {
            id: 12,
            content: 'reply',
            visibility: 'public',
            is_spoiler: false,
          },
        }),
      ),
    ).toBe(`${routes.communityPost(9)}#comment-12`);
  });

  it('uses the explicit owner for collection activity', () => {
    expect(
      activityTargetHref(
        activity({
          activity_type: 'collection_created',
          collection: { id: 7, name: 'List', simple_rating: null, note: '', is_public: true },
        }),
        routes.home,
        23,
      ),
    ).toBe(routes.userCollection(23, 7));
  });

  it('returns the caller fallback for an activity with no navigable target', () => {
    expect(activityTargetHref(activity({ activity_type: 'future-event' }), routes.home)).toBe(routes.home);
  });
});
