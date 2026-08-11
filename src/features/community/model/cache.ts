import type { QueryClient } from '@tanstack/react-query';
import { communityQueryKeys } from '@/entities/community';
import { libraryQueryKeys } from '@/entities/library';
import { publicUserQueryKeys } from '@/entities/user';

export async function invalidateCommunityTargets(queryClient: QueryClient) {
  await Promise.all([
    invalidateCommunityTargetSummaries(queryClient),
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.comments() }),
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.bookmarks() }),
  ]);
}

export async function invalidateCommunityTargetSummaries(queryClient: QueryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.activities() }),
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.posts() }),
    queryClient.invalidateQueries({ queryKey: libraryQueryKeys.reviews() }),
    queryClient.invalidateQueries({ queryKey: libraryQueryKeys.collections() }),
    queryClient.invalidateQueries({ queryKey: publicUserQueryKeys.all }),
  ]);
}

export async function invalidateCommunityFollows(queryClient: QueryClient, userId?: number) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.follows() }),
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.activities() }),
    queryClient.invalidateQueries({ queryKey: publicUserQueryKeys.all }),
    userId ? queryClient.invalidateQueries({ queryKey: publicUserQueryKeys.publicProfile(userId) }) : Promise.resolve(),
  ]);
}
