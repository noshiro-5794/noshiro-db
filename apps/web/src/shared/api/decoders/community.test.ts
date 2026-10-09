import { describe, expect, it } from 'vitest';
import {
  decodeCommunityNotification,
  decodeCommunityPost,
  decodeNotificationReadAllResult,
  decodeNotificationUnreadCount,
} from './community';

const user = { id: 1, nickname: 'User', avatar: '' };

describe('community response decoders', () => {
  it('validates post viewer permissions and counters', () => {
    const post = {
      id: 1,
      content: 'Post',
      visibility: 'public',
      is_spoiler: false,
      is_nsfw: false,
      author: user,
      reply_count: 0,
      viewer_state: { has_liked: false, has_bookmarked: true, is_following_author: false },
    };
    expect(decodeCommunityPost(post)).toEqual(post);
    expect(() => decodeCommunityPost({ ...post, viewer_state: { ...post.viewer_state, has_liked: 1 } })).toThrow(
      TypeError,
    );
  });

  it('validates notification identity, target and read state', () => {
    const notification = {
      id: 2,
      notification_type: 'comment_created',
      actor: user,
      target: { type: 'post', id: 1, author: user },
      metadata: {},
      is_read: false,
      read_at: null,
      created_at: '2026-07-29T00:00:00Z',
    };
    expect(decodeCommunityNotification(notification)).toEqual(notification);
    expect(() => decodeCommunityNotification({ ...notification, target: { type: 'post', id: 0 } })).toThrow(TypeError);
  });

  it('keeps unread and read-all counters as distinct contracts', () => {
    expect(decodeNotificationUnreadCount({ unread_count: 3 })).toEqual({ unread_count: 3 });
    expect(decodeNotificationReadAllResult({ updated_count: 3 })).toEqual({ updated_count: 3 });
    expect(() => decodeNotificationReadAllResult({ unread_count: 3 })).toThrow(TypeError);
  });
});
