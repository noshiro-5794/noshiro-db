import { mutationOptions, queryOptions } from '@tanstack/react-query';
import {
  communityActivitiesApi,
  communityCommentsApi,
  communityFollowsApi,
  communityInteractionsApi,
  communityNotificationsApi,
  communityPostsApi,
  communityRelationshipsApi,
  communityReportsApi,
  type CommunityActivityListQuery,
  type CommunityBookmarkListQuery,
  type CommunityCommentBody,
  type CommunityCommentListQuery,
  type CommunityNotificationListQuery,
  type CommunityPostBody,
  type CommunityPostListQuery,
  type CommunityReportListQuery,
} from '@/features/community/api';
import type { CommunityReactionType, CommunityReportReason, CommunityReportStatus, CommunityTargetType, PageQuery } from '@/lib/api/types';

export const communityQueryKeys = {
  all: ['community'] as const,
  follows: () => [...communityQueryKeys.all, 'follows'] as const,
  myFollowing: (query: PageQuery = {}) => [...communityQueryKeys.follows(), 'my-following', query] as const,
  myFollowers: (query: PageQuery = {}) => [...communityQueryKeys.follows(), 'my-followers', query] as const,
  userFollowing: (userId: number, query: PageQuery = {}) => [...communityQueryKeys.follows(), 'user-following', userId, query] as const,
  userFollowers: (userId: number, query: PageQuery = {}) => [...communityQueryKeys.follows(), 'user-followers', userId, query] as const,
  relationships: () => [...communityQueryKeys.all, 'relationships'] as const,
  blocks: (query: PageQuery = {}) => [...communityQueryKeys.relationships(), 'blocks', query] as const,
  mutes: (query: PageQuery = {}) => [...communityQueryKeys.relationships(), 'mutes', query] as const,
  activities: () => [...communityQueryKeys.all, 'activities'] as const,
  publicActivities: (query: CommunityActivityListQuery = {}) => [...communityQueryKeys.activities(), 'public', query] as const,
  myActivities: (query: CommunityActivityListQuery = {}) => [...communityQueryKeys.activities(), 'mine', query] as const,
  feed: (query: CommunityActivityListQuery = {}) => [...communityQueryKeys.activities(), 'feed', query] as const,
  userActivities: (userId: number, query: CommunityActivityListQuery = {}) => [...communityQueryKeys.activities(), 'user', userId, query] as const,
  posts: () => [...communityQueryKeys.all, 'posts'] as const,
  postList: (query: CommunityPostListQuery = {}) => [...communityQueryKeys.posts(), 'list', query] as const,
  postDetail: (postId: number) => [...communityQueryKeys.posts(), 'detail', postId] as const,
  postComments: (postId: number, query: PageQuery = {}) => [...communityQueryKeys.posts(), 'comments', postId, query] as const,
  comments: () => [...communityQueryKeys.all, 'comments'] as const,
  commentList: (query: CommunityCommentListQuery) => [...communityQueryKeys.comments(), 'list', query] as const,
  bookmarks: (query: CommunityBookmarkListQuery = {}) => [...communityQueryKeys.all, 'bookmarks', query] as const,
  notifications: () => [...communityQueryKeys.all, 'notifications'] as const,
  notificationList: (query: CommunityNotificationListQuery = {}) => [...communityQueryKeys.notifications(), 'list', query] as const,
  unreadCount: () => [...communityQueryKeys.notifications(), 'unread-count'] as const,
  reports: () => [...communityQueryKeys.all, 'reports'] as const,
  myReports: (query: CommunityReportListQuery = {}) => [...communityQueryKeys.reports(), 'mine', query] as const,
  staffReports: (query: CommunityReportListQuery = {}) => [...communityQueryKeys.reports(), 'staff', query] as const,
};

export const communityQueries = {
  myFollowing: (query: PageQuery = {}) => queryOptions({ queryKey: communityQueryKeys.myFollowing(query), queryFn: () => communityFollowsApi.listMyFollowing(query) }),
  myFollowers: (query: PageQuery = {}) => queryOptions({ queryKey: communityQueryKeys.myFollowers(query), queryFn: () => communityFollowsApi.listMyFollowers(query) }),
  userFollowing: (userId: number, query: PageQuery = {}) =>
    queryOptions({ queryKey: communityQueryKeys.userFollowing(userId, query), queryFn: () => communityFollowsApi.listUserFollowing(userId, query) }),
  userFollowers: (userId: number, query: PageQuery = {}) =>
    queryOptions({ queryKey: communityQueryKeys.userFollowers(userId, query), queryFn: () => communityFollowsApi.listUserFollowers(userId, query) }),
  blocks: (query: PageQuery = {}) => queryOptions({ queryKey: communityQueryKeys.blocks(query), queryFn: () => communityRelationshipsApi.listBlocks(query) }),
  mutes: (query: PageQuery = {}) => queryOptions({ queryKey: communityQueryKeys.mutes(query), queryFn: () => communityRelationshipsApi.listMutes(query) }),
  myActivities: (query: CommunityActivityListQuery = {}) => queryOptions({ queryKey: communityQueryKeys.myActivities(query), queryFn: () => communityActivitiesApi.listMine(query) }),
  publicActivities: (query: CommunityActivityListQuery = {}) => queryOptions({ queryKey: communityQueryKeys.publicActivities(query), queryFn: () => communityActivitiesApi.listPublic(query) }),
  feed: (query: CommunityActivityListQuery = {}) => queryOptions({ queryKey: communityQueryKeys.feed(query), queryFn: () => communityActivitiesApi.listFeed(query) }),
  userActivities: (userId: number, query: CommunityActivityListQuery = {}) =>
    queryOptions({ queryKey: communityQueryKeys.userActivities(userId, query), queryFn: () => communityActivitiesApi.listUser(userId, query) }),
  posts: (query: CommunityPostListQuery = {}) => queryOptions({ queryKey: communityQueryKeys.postList(query), queryFn: () => communityPostsApi.list(query) }),
  post: (postId: number) => queryOptions({ queryKey: communityQueryKeys.postDetail(postId), queryFn: () => communityPostsApi.get(postId) }),
  postComments: (postId: number, query: PageQuery = {}) =>
    queryOptions({ queryKey: communityQueryKeys.postComments(postId, query), queryFn: () => communityPostsApi.listComments(postId, query) }),
  comments: (query: CommunityCommentListQuery) => queryOptions({ queryKey: communityQueryKeys.commentList(query), queryFn: () => communityCommentsApi.list(query) }),
  bookmarks: (query: CommunityBookmarkListQuery = {}) => queryOptions({ queryKey: communityQueryKeys.bookmarks(query), queryFn: () => communityInteractionsApi.listBookmarks(query) }),
  notifications: (query: CommunityNotificationListQuery = {}) =>
    queryOptions({ queryKey: communityQueryKeys.notificationList(query), queryFn: () => communityNotificationsApi.list(query) }),
  unreadCount: () => queryOptions({ queryKey: communityQueryKeys.unreadCount(), queryFn: () => communityNotificationsApi.unreadCount() }),
  myReports: (query: CommunityReportListQuery = {}) => queryOptions({ queryKey: communityQueryKeys.myReports(query), queryFn: () => communityReportsApi.listMine(query) }),
  staffReports: (query: CommunityReportListQuery = {}) => queryOptions({ queryKey: communityQueryKeys.staffReports(query), queryFn: () => communityReportsApi.listStaff(query) }),
};

export const communityMutations = {
  follow: () => mutationOptions({ mutationFn: (targetUserId: number) => communityFollowsApi.follow(targetUserId) }),
  unfollow: () => mutationOptions({ mutationFn: (targetUserId: number) => communityFollowsApi.unfollow(targetUserId) }),
  block: () => mutationOptions({ mutationFn: ({ targetUserId, reason }: { targetUserId: number; reason?: string }) => communityRelationshipsApi.block(targetUserId, { reason }) }),
  unblock: () => mutationOptions({ mutationFn: (targetUserId: number) => communityRelationshipsApi.unblock(targetUserId) }),
  mute: () => mutationOptions({ mutationFn: ({ targetUserId, reason }: { targetUserId: number; reason?: string }) => communityRelationshipsApi.mute(targetUserId, { reason }) }),
  unmute: () => mutationOptions({ mutationFn: (targetUserId: number) => communityRelationshipsApi.unmute(targetUserId) }),
  createPost: () => mutationOptions({ mutationFn: (body: CommunityPostBody) => communityPostsApi.create(body) }),
  updatePost: () => mutationOptions({ mutationFn: ({ postId, body }: { postId: number; body: Partial<CommunityPostBody> }) => communityPostsApi.update(postId, body) }),
  deletePost: () => mutationOptions({ mutationFn: (postId: number) => communityPostsApi.delete(postId) }),
  createPostComment: () =>
    mutationOptions({ mutationFn: ({ postId, body }: { postId: number; body: Omit<CommunityCommentBody, 'target_type' | 'target_id'> }) => communityPostsApi.createComment(postId, body) }),
  createComment: () =>
    mutationOptions({ mutationFn: (body: CommunityCommentBody & { target_type: CommunityTargetType; target_id: number }) => communityCommentsApi.create(body) }),
  updateComment: () =>
    mutationOptions({ mutationFn: ({ commentId, body }: { commentId: number; body: Partial<Pick<CommunityCommentBody, 'content' | 'visibility' | 'is_spoiler'>> }) => communityCommentsApi.update(commentId, body) }),
  deleteComment: () => mutationOptions({ mutationFn: (commentId: number) => communityCommentsApi.delete(commentId) }),
  react: () => mutationOptions({ mutationFn: (body: { target_type: CommunityTargetType; target_id: number; reaction_type?: CommunityReactionType }) => communityInteractionsApi.react(body) }),
  unreact: () => mutationOptions({ mutationFn: (body: { target_type: CommunityTargetType; target_id: number; reaction_type?: CommunityReactionType }) => communityInteractionsApi.unreact(body) }),
  bookmark: () => mutationOptions({ mutationFn: (body: { target_type: CommunityTargetType; target_id: number }) => communityInteractionsApi.bookmark(body) }),
  unbookmark: () => mutationOptions({ mutationFn: (body: { target_type: CommunityTargetType; target_id: number }) => communityInteractionsApi.unbookmark(body) }),
  markNotificationRead: () => mutationOptions({ mutationFn: (notificationId: number) => communityNotificationsApi.markRead(notificationId) }),
  markAllNotificationsRead: () => mutationOptions({ mutationFn: () => communityNotificationsApi.markAllRead() }),
  createReport: () =>
    mutationOptions({ mutationFn: (body: { target_type: CommunityTargetType; target_id: number; reason: CommunityReportReason; description?: string }) => communityReportsApi.create(body) }),
  resolveReport: () =>
    mutationOptions({ mutationFn: ({ reportId, body }: { reportId: number; body: { status: CommunityReportStatus; action_type?: string; moderation_reason?: string } }) => communityReportsApi.resolve(reportId, body) }),
};
