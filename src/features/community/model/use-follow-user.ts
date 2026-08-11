import { useMutation, useQueryClient } from '@tanstack/react-query';
import { communityFollowsApi } from '@/entities/community';
import { publicUserQueryKeys } from '@/entities/user';
import type { PublicUserProfile } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { toast } from '@/shared/ui/toast';
import { invalidateCommunityFollows } from './cache';
import { optimisticFollowProfile } from './follow-state';

type FollowUserVariables = {
  shouldFollow: boolean;
  targetUserId: number;
};

export function useFollowUserMutation() {
  const { t } = useI18n();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shouldFollow, targetUserId }: FollowUserVariables) =>
      shouldFollow ? communityFollowsApi.follow(targetUserId) : communityFollowsApi.unfollow(targetUserId),
    onMutate: async ({ shouldFollow, targetUserId }) => {
      const queryKey = publicUserQueryKeys.publicProfile(targetUserId);
      await queryClient.cancelQueries({ queryKey });
      const previousProfile = queryClient.getQueryData<PublicUserProfile>(queryKey);
      if (previousProfile) {
        queryClient.setQueryData(queryKey, optimisticFollowProfile(previousProfile, shouldFollow));
      }
      return { previousProfile, queryKey };
    },
    onError: (_error, _variables, context) => {
      if (context?.previousProfile) queryClient.setQueryData(context.queryKey, context.previousProfile);
      toast.error(t('common.requestFailed'));
    },
    onSettled: async (_data, _error, variables) => {
      await invalidateCommunityFollows(queryClient, variables.targetUserId);
    },
  });
}
