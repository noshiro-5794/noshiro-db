import { describe, expect, it } from 'vitest';
import type { PublicUserProfile } from '@/shared/api';
import { optimisticFollowProfile } from './follow-state';

const profile: PublicUserProfile = {
  id: 7,
  nickname: 'Noshiro',
  avatar: null,
  bio: '',
  is_following: false,
  stats: {
    collection_count: 0,
    follower_count: 2,
    following_count: 0,
    review_count: 0,
    subject_count: 0,
  },
};

describe('optimistic follow profile', () => {
  it('updates the relationship and follower count once', () => {
    const followed = optimisticFollowProfile(profile, true);

    expect(followed.is_following).toBe(true);
    expect(followed.stats.follower_count).toBe(3);
    expect(optimisticFollowProfile(followed, true)).toBe(followed);
  });

  it('never produces a negative follower count', () => {
    const followed = { ...profile, is_following: true, stats: { ...profile.stats, follower_count: 0 } };
    expect(optimisticFollowProfile(followed, false).stats.follower_count).toBe(0);
  });
});
