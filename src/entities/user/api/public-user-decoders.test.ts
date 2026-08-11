import { describe, expect, it } from 'vitest';
import { decodePublicUserProfile } from './public-user-decoders';

const profile = {
  id: 42,
  nickname: 'User',
  avatar: '',
  bio: 'Hello',
  stats: {
    subject_count: 3,
    review_count: 2,
    collection_count: 1,
    following_count: 4,
    follower_count: 5,
  },
  is_following: true,
};

describe('public user response decoder', () => {
  it('accepts the backend profile contract and strips unknown fields', () => {
    expect(decodePublicUserProfile({ ...profile, ignored: true })).toEqual(profile);
  });

  it.each([
    { ...profile, id: '42' },
    { ...profile, is_following: 1 },
    { ...profile, stats: { ...profile.stats, follower_count: -1 } },
    { ...profile, stats: null },
  ])('rejects malformed public profile data', (value) => {
    expect(() => decodePublicUserProfile(value)).toThrow(TypeError);
  });
});
