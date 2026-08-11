import type { QueryClient } from '@tanstack/react-query';
import { communityQueryKeys } from '@/entities/community';
import { libraryQueryKeys } from '@/entities/library';
import { publicUserQueryKeys } from '@/entities/user';

export async function invalidateCollectionViews(
  queryClient: QueryClient,
  options: { includeComments?: boolean; userId?: number | undefined } = {},
) {
  const publicUserKey = options.userId ? publicUserQueryKeys.user(options.userId) : publicUserQueryKeys.all;
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: libraryQueryKeys.collections() }),
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.activities() }),
    queryClient.invalidateQueries({ queryKey: communityQueryKeys.bookmarks() }),
    queryClient.invalidateQueries({ queryKey: publicUserKey }),
    options.includeComments
      ? queryClient.invalidateQueries({ queryKey: communityQueryKeys.comments() })
      : Promise.resolve(),
  ]);
}
