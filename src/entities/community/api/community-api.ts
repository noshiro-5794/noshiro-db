import {
  api,
  apiRequest,
  decodeActivity,
  decodeApiPage,
  decodeCommunityBookmark,
  decodeCommunityComment,
  decodeCommunityNotification,
  decodeCommunityPost,
  decodeCommunityReaction,
  decodeCommunityRelationship,
  decodeCommunityReport,
  decodeFollowRelation,
  decodeNotificationReadAllResult,
  decodeNotificationUnreadCount,
  encodePath,
} from '@/shared/api';
import type {
  Activity,
  ActivityType,
  ApiPage,
  ApiRequestContext,
  CommunityBookmark,
  CommunityCommentSummary,
  CommunityNotification,
  CommunityNotificationReadAllResult,
  CommunityNotificationUnreadCount,
  CommunityPostSummary,
  CommunityReaction,
  CommunityReactionType,
  CommunityRelationship,
  CommunityReport,
  CommunityReportReason,
  CommunityReportStatus,
  CommunityTargetType,
  CommunityVisibility,
  FollowRelation,
  PageQuery,
} from '@/shared/api';

export type CommunityActivityListQuery = PageQuery & {
  activity_type?: ActivityType;
  include_self?: boolean;
  ordering?: 'id' | '-id' | 'created_at' | '-created_at';
};

export type CommunityPostListQuery = PageQuery & {
  author_id?: number;
  post_type?: string;
  subject_id?: string;
  keyword?: string;
  ordering?:
    | '-last_activity_at'
    | 'last_activity_at'
    | '-created_at'
    | 'created_at'
    | '-reaction_count'
    | 'reaction_count'
    | '-reply_count'
    | 'reply_count';
};

export type CommunityPostBody = {
  subject_id?: string;
  content: string;
  visibility?: CommunityVisibility;
  is_spoiler?: boolean;
  is_nsfw?: boolean;
};

export type CommunityCommentListQuery = PageQuery & {
  target_type: CommunityTargetType;
  target_id: number;
};

export type CommunityCommentBody = {
  target_type?: CommunityTargetType;
  target_id?: number;
  parent_id?: number;
  content: string;
  visibility?: CommunityVisibility;
  is_spoiler?: boolean;
};

export type CommunityBookmarkListQuery = PageQuery & {
  target_type?: CommunityTargetType;
  keyword?: string;
};

export type CommunityNotificationListQuery = PageQuery & {
  is_read?: boolean;
};

export type CommunityReportListQuery = PageQuery & {
  status?: CommunityReportStatus;
};

export const communityFollowsApi = {
  follow: (targetUserId: number) =>
    api.post<FollowRelation>(`/api/community/me/following/${encodePath(targetUserId)}/`, undefined, {
      decode: decodeFollowRelation,
    }),
  unfollow: (targetUserId: number) => api.delete<unknown>(`/api/community/me/following/${encodePath(targetUserId)}/`),
  listMyFollowing: (query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<FollowRelation>>('/api/community/me/following/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeFollowRelation),
      query,
    }),
  listMyFollowers: (query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<FollowRelation>>('/api/community/me/followers/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeFollowRelation),
      query,
    }),
  listUserFollowing: (userId: number, query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<FollowRelation>>(`/api/community/users/${encodePath(userId)}/following/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeFollowRelation),
      query,
    }),
  listUserFollowers: (userId: number, query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<FollowRelation>>(`/api/community/users/${encodePath(userId)}/followers/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeFollowRelation),
      query,
    }),
};

export const communityRelationshipsApi = {
  listBlocks: (query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityRelationship>>('/api/community/me/blocks/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityRelationship),
      query,
    }),
  block: (targetUserId: number, body: { reason?: string } = {}) =>
    api.post<CommunityRelationship, typeof body>(`/api/community/me/blocks/${encodePath(targetUserId)}/`, body, {
      decode: decodeCommunityRelationship,
    }),
  unblock: (targetUserId: number) => api.delete<unknown>(`/api/community/me/blocks/${encodePath(targetUserId)}/`),
  listMutes: (query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityRelationship>>('/api/community/me/mutes/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityRelationship),
      query,
    }),
  mute: (targetUserId: number, body: { reason?: string } = {}) =>
    api.post<CommunityRelationship, typeof body>(`/api/community/me/mutes/${encodePath(targetUserId)}/`, body, {
      decode: decodeCommunityRelationship,
    }),
  unmute: (targetUserId: number) => api.delete<unknown>(`/api/community/me/mutes/${encodePath(targetUserId)}/`),
};

export const communityActivitiesApi = {
  listPublic: (query: CommunityActivityListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Activity>>('/api/community/activities/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeActivity),
      query,
    }),
  listMine: (query: CommunityActivityListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Activity>>('/api/community/me/activities/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeActivity),
      query,
    }),
  listFeed: (query: CommunityActivityListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Activity>>('/api/community/me/feed/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeActivity),
      query,
    }),
  listUser: (userId: number, query: CommunityActivityListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Activity>>(`/api/community/users/${encodePath(userId)}/activities/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeActivity),
      query,
    }),
};

export const communityPostsApi = {
  list: (query: CommunityPostListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityPostSummary>>('/api/community/posts/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityPost),
      query,
    }),
  create: (body: CommunityPostBody) =>
    api.post<CommunityPostSummary, CommunityPostBody>('/api/community/posts/', body, {
      decode: decodeCommunityPost,
    }),
  get: (postId: number, context: ApiRequestContext = {}) =>
    api.get<CommunityPostSummary>(`/api/community/posts/${encodePath(postId)}/`, {
      ...context,
      decode: decodeCommunityPost,
    }),
  update: (postId: number, body: Partial<CommunityPostBody>) =>
    api.patch<CommunityPostSummary, Partial<CommunityPostBody>>(`/api/community/posts/${encodePath(postId)}/`, body, {
      decode: decodeCommunityPost,
    }),
  delete: (postId: number) => api.delete<unknown>(`/api/community/posts/${encodePath(postId)}/`),
};

export const communityCommentsApi = {
  list: (query: CommunityCommentListQuery, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityCommentSummary>>('/api/community/comments/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityComment),
      query,
    }),
  create: (body: CommunityCommentBody & { target_type: CommunityTargetType; target_id: number }) =>
    api.post<CommunityCommentSummary, typeof body>('/api/community/comments/', body, {
      decode: decodeCommunityComment,
    }),
  update: (commentId: number, body: Partial<Pick<CommunityCommentBody, 'content' | 'visibility' | 'is_spoiler'>>) =>
    api.patch<CommunityCommentSummary, typeof body>(`/api/community/comments/${encodePath(commentId)}/`, body, {
      decode: decodeCommunityComment,
    }),
  delete: (commentId: number) => api.delete<unknown>(`/api/community/comments/${encodePath(commentId)}/`),
};

export const communityInteractionsApi = {
  react: (body: { target_type: CommunityTargetType; target_id: number; reaction_type?: CommunityReactionType }) =>
    api.post<CommunityReaction, typeof body>('/api/community/reactions/', body, {
      decode: decodeCommunityReaction,
    }),
  unreact: (body: { target_type: CommunityTargetType; target_id: number; reaction_type?: CommunityReactionType }) =>
    apiRequest<unknown, typeof body>('/api/community/reactions/', { method: 'DELETE', body }),
  listBookmarks: (query: CommunityBookmarkListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityBookmark>>('/api/community/bookmarks/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityBookmark),
      query,
    }),
  bookmark: (body: { target_type: CommunityTargetType; target_id: number }) =>
    api.post<CommunityBookmark, typeof body>('/api/community/bookmarks/', body, {
      decode: decodeCommunityBookmark,
    }),
  unbookmark: (body: { target_type: CommunityTargetType; target_id: number }) =>
    apiRequest<unknown, typeof body>('/api/community/bookmarks/', { method: 'DELETE', body }),
};

export const communityNotificationsApi = {
  list: (query: CommunityNotificationListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityNotification>>('/api/community/notifications/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityNotification),
      query,
    }),
  unreadCount: (context: ApiRequestContext = {}) =>
    api.get<CommunityNotificationUnreadCount>('/api/community/notifications/unread-count/', {
      ...context,
      decode: decodeNotificationUnreadCount,
    }),
  markRead: (notificationId: number) =>
    api.patch<CommunityNotification>(`/api/community/notifications/${encodePath(notificationId)}/read/`, undefined, {
      decode: decodeCommunityNotification,
    }),
  markAllRead: () =>
    api.post<CommunityNotificationReadAllResult>('/api/community/notifications/read-all/', undefined, {
      decode: decodeNotificationReadAllResult,
    }),
};

export const communityReportsApi = {
  create: (body: {
    target_type: CommunityTargetType;
    target_id: number;
    reason: CommunityReportReason;
    description?: string;
  }) => api.post<CommunityReport, typeof body>('/api/community/reports/', body, { decode: decodeCommunityReport }),
  listMine: (query: CommunityReportListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityReport>>('/api/community/me/reports/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityReport),
      query,
    }),
  listStaff: (query: CommunityReportListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityReport>>('/api/community/staff/reports/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityReport),
      query,
    }),
  resolve: (
    reportId: number,
    body: { status: CommunityReportStatus; action_type?: string; moderation_reason?: string },
  ) =>
    api.patch<CommunityReport, typeof body>(`/api/community/staff/reports/${encodePath(reportId)}/resolve/`, body, {
      decode: decodeCommunityReport,
    }),
};
