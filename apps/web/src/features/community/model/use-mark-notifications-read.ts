import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query';
import { communityNotificationsApi, communityQueryKeys } from '@/entities/community';
import type {
  ApiPage,
  CommunityNotification,
  CommunityNotificationReadAllResult,
  CommunityNotificationUnreadCount,
} from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { toast } from '@/shared/ui/toast';
import {
  markNotificationsReadInPage,
  nextUnreadCount,
  wasNotificationUnread,
  type MarkNotificationsReadTarget,
} from './notification-state';

type NotificationPageSnapshot = [QueryKey, ApiPage<CommunityNotification> | undefined];

type NotificationMutationContext = {
  pageSnapshots: NotificationPageSnapshot[];
  unreadCountKey: QueryKey;
  unreadCountSnapshot: CommunityNotificationUnreadCount | undefined;
};

function isNotificationListQuery(queryKey: readonly unknown[]) {
  return queryKey[2] === 'list';
}

export function useMarkNotificationsReadMutation() {
  const { t } = useI18n();
  const queryClient = useQueryClient();

  return useMutation<
    CommunityNotificationReadAllResult | CommunityNotification,
    Error,
    MarkNotificationsReadTarget,
    NotificationMutationContext
  >({
    mutationFn: async (target) =>
      target.kind === 'all'
        ? await communityNotificationsApi.markAllRead()
        : await communityNotificationsApi.markRead(target.notificationId),
    scope: { id: 'community-notifications-read' },
    onMutate: async (target) => {
      const notificationsKey = communityQueryKeys.notifications();
      await queryClient.cancelQueries({ queryKey: notificationsKey });

      const pageSnapshots = queryClient.getQueriesData<ApiPage<CommunityNotification>>({
        queryKey: notificationsKey,
        predicate: (query) => isNotificationListQuery(query.queryKey),
      }) as NotificationPageSnapshot[];
      const unreadCountKey = communityQueryKeys.unreadCount();
      const unreadCountSnapshot = queryClient.getQueryData<CommunityNotificationUnreadCount>(unreadCountKey);
      const targetWasUnread =
        target.kind === 'one' &&
        wasNotificationUnread(
          pageSnapshots.map(([, page]) => page),
          target.notificationId,
        );
      const readAt = new Date().toISOString();

      for (const [queryKey, page] of pageSnapshots) {
        if (page) queryClient.setQueryData(queryKey, markNotificationsReadInPage(page, target, readAt));
      }
      if (unreadCountSnapshot) {
        queryClient.setQueryData<CommunityNotificationUnreadCount>(unreadCountKey, {
          unread_count: nextUnreadCount(unreadCountSnapshot.unread_count, target, targetWasUnread),
        });
      }

      return { pageSnapshots, unreadCountKey, unreadCountSnapshot };
    },
    onError: (_error, _target, context) => {
      for (const [queryKey, page] of context?.pageSnapshots ?? []) {
        queryClient.setQueryData(queryKey, page);
      }
      if (context?.unreadCountSnapshot) {
        queryClient.setQueryData(context.unreadCountKey, context.unreadCountSnapshot);
      }
      toast.error(t('common.requestFailed'));
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: communityQueryKeys.notifications() });
    },
  });
}
