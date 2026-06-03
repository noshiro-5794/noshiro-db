import type { QueryClient } from '@tanstack/react-query';
import { communityQueryKeys } from '@/features/community/community-queries';
import { socialQueryKeys } from '@/features/social/social-queries';

export async function invalidateCommunityTargets(queryClient: QueryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.activities() }),
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.posts() }),
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.comments() }),
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.bookmarks() }),
    queryClient.invalidateQueries({ queryKey: socialQueryKeys.activities() }),
    queryClient.invalidateQueries({ queryKey: socialQueryKeys.publicUsers() }),
  ]);
}

export async function invalidateCommunityFollows(queryClient: QueryClient, userId?: number) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.follows() }),
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.activities() }),
    queryClient.invalidateQueries({ queryKey: socialQueryKeys.follows() }),
    queryClient.invalidateQueries({ queryKey: socialQueryKeys.activities() }),
    queryClient.invalidateQueries({ queryKey: socialQueryKeys.publicUsers() }),
    userId ? queryClient.invalidateQueries({ queryKey: socialQueryKeys.publicProfile(userId) }) : Promise.resolve(),
  ]);
}
