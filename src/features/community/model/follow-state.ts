import type { PublicUserProfile } from '@/shared/api';

export function optimisticFollowProfile(profile: PublicUserProfile, shouldFollow: boolean): PublicUserProfile {
  if (profile.is_following === shouldFollow) return profile;
  return {
    ...profile,
    is_following: shouldFollow,
    stats: {
      ...profile.stats,
      follower_count: Math.max(0, profile.stats.follower_count + (shouldFollow ? 1 : -1)),
    },
  };
}
