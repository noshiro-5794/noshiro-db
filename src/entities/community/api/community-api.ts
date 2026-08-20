import {
  api,
  apiRequest,
  decodeActivity,
  decodeApiPage,
  decodeCursorPage,
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
  CursorPage,
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

export type CommunityActivityListQuery = {
  cursor?: string;
  page_size?: number;
  activity_type?: ActivityType;
  include_self?: boolean;
  ordering?: 'id' | '-id' | 'created_at' | '-created_at';
};

export type CommunityPostListQuery = PageQuery & {
  author_id?: number;
  post_type?: string;
  entity_id?: string;
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
  entity_id?: string;
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

export type CommunityNotificationListQuery = {
  cursor?: string;
  page_size?: number;
  is_read?: boolean;
};

export type CommunityReportListQuery = PageQuery & {
  status?: CommunityReportStatus;
};

export const communityFollowsApi = {
  follow: (targetUserId: number) =>
    api.put<FollowRelation>(`/api/v1/community/me/following/${encodePath(targetUserId)}/`, undefined, {
      decode: decodeFollowRelation,
    }),
  unfollow: (targetUserId: number) => api.delete<unknown>(`/api/v1/community/me/following/${encodePath(targetUserId)}/`),
  listMyFollowing: (query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<FollowRelation>>('/api/v1/community/me/following/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeFollowRelation),
      query,
    }),
  listMyFollowers: (query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<FollowRelation>>('/api/v1/community/me/followers/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeFollowRelation),
      query,
    }),
  listUserFollowing: (userId: number, query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<FollowRelation>>(`/api/v1/community/users/${encodePath(userId)}/following/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeFollowRelation),
      query,
    }),
  listUserFollowers: (userId: number, query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<FollowRelation>>(`/api/v1/community/users/${encodePath(userId)}/followers/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeFollowRelation),
      query,
    }),
};

export const communityRelationshipsApi = {
  listBlocks: (query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityRelationship>>('/api/v1/community/me/blocks/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityRelationship),
      query,
    }),
  block: (targetUserId: number, body: { reason?: string } = {}) =>
    api.put<CommunityRelationship, typeof body>(`/api/v1/community/me/blocks/${encodePath(targetUserId)}/`, body, {
      decode: decodeCommunityRelationship,
    }),
  unblock: (targetUserId: number) => api.delete<unknown>(`/api/v1/community/me/blocks/${encodePath(targetUserId)}/`),
  listMutes: (query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityRelationship>>('/api/v1/community/me/mutes/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityRelationship),
      query,
    }),
  mute: (targetUserId: number, body: { reason?: string } = {}) =>
    api.put<CommunityRelationship, typeof body>(`/api/v1/community/me/mutes/${encodePath(targetUserId)}/`, body, {
      decode: decodeCommunityRelationship,
    }),
  unmute: (targetUserId: number) => api.delete<unknown>(`/api/v1/community/me/mutes/${encodePath(targetUserId)}/`),
};

export const communityActivitiesApi = {
  listPublic: (query: CommunityActivityListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<CursorPage<Activity>>('/api/v1/community/activities/', {
      ...context,
      decode: (value) => decodeCursorPage(value, decodeActivity),
      query,
    }),
  listMine: (query: CommunityActivityListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<CursorPage<Activity>>('/api/v1/community/me/activities/', {
      ...context,
      decode: (value) => decodeCursorPage(value, decodeActivity),
      query,
    }),
  listFeed: (query: CommunityActivityListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<CursorPage<Activity>>('/api/v1/community/me/feed/', {
      ...context,
      decode: (value) => decodeCursorPage(value, decodeActivity),
      query,
    }),
  listUser: (userId: number, query: CommunityActivityListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<CursorPage<Activity>>(`/api/v1/community/users/${encodePath(userId)}/activities/`, {
      ...context,
      decode: (value) => decodeCursorPage(value, decodeActivity),
      query,
    }),
};

export const communityPostsApi = {
  list: (query: CommunityPostListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityPostSummary>>('/api/v1/community/posts/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityPost),
      query: {
        ...(query.entity_id ? { entity_id: query.entity_id } : {}),
        ...(query.keyword ? { keyword: query.keyword } : {}),
        ...(query.ordering ? { ordering: query.ordering } : {}),
        ...(query.page === undefined ? {} : { page: query.page }),
        ...(query.page_size === undefined ? {} : { page_size: query.page_size }),
      },
    }),
  create: (body: CommunityPostBody) =>
    api.post<CommunityPostSummary, CommunityPostBody>('/api/v1/community/posts/', body, {
      decode: decodeCommunityPost,
    }),
  get: (postId: number, context: ApiRequestContext = {}) =>
    api.get<CommunityPostSummary>(`/api/v1/community/posts/${encodePath(postId)}/`, {
      ...context,
      decode: decodeCommunityPost,
    }),
  update: (postId: number, body: Partial<CommunityPostBody>) =>
    api.patch<CommunityPostSummary, Partial<CommunityPostBody>>(`/api/v1/community/posts/${encodePath(postId)}/`, body, {
      decode: decodeCommunityPost,
    }),
  delete: (postId: number) => api.delete<unknown>(`/api/v1/community/posts/${encodePath(postId)}/`),
};

export const communityCommentsApi = {
  list: (query: CommunityCommentListQuery, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityCommentSummary>>('/api/v1/community/comments/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityComment),
      query,
    }),
  create: (body: CommunityCommentBody & { target_type: CommunityTargetType; target_id: number }) =>
    api.post<CommunityCommentSummary, typeof body>('/api/v1/community/comments/', body, {
      decode: decodeCommunityComment,
    }),
  update: (commentId: number, body: Partial<Pick<CommunityCommentBody, 'content' | 'visibility' | 'is_spoiler'>>) =>
    api.patch<CommunityCommentSummary, typeof body>(`/api/v1/community/comments/${encodePath(commentId)}/`, body, {
      decode: decodeCommunityComment,
    }),
  delete: (commentId: number) => api.delete<unknown>(`/api/v1/community/comments/${encodePath(commentId)}/`),
};

export const communityInteractionsApi = {
  react: (body: { target_type: CommunityTargetType; target_id: number; reaction_type?: CommunityReactionType }) =>
    api.put<CommunityReaction, undefined>(
      `/api/v1/community/me/reactions/${encodePath(body.target_type)}/${encodePath(body.target_id)}/${encodePath(body.reaction_type ?? 'like')}/`,
      undefined,
      {
      decode: decodeCommunityReaction,
      },
    ),
  unreact: (body: { target_type: CommunityTargetType; target_id: number; reaction_type?: CommunityReactionType }) =>
    apiRequest<unknown>(`/api/v1/community/me/reactions/${encodePath(body.target_type)}/${encodePath(body.target_id)}/${encodePath(body.reaction_type ?? 'like')}/`, {
      method: 'DELETE',
    }),
  listBookmarks: (query: CommunityBookmarkListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityBookmark>>('/api/v1/community/me/bookmarks/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityBookmark),
      query,
    }),
  bookmark: (body: { target_type: CommunityTargetType; target_id: number }) =>
    api.put<CommunityBookmark, undefined>(`/api/v1/community/me/bookmarks/${encodePath(body.target_type)}/${encodePath(body.target_id)}/`, undefined, {
      decode: decodeCommunityBookmark,
    }),
  unbookmark: (body: { target_type: CommunityTargetType; target_id: number }) =>
    apiRequest<unknown>(`/api/v1/community/me/bookmarks/${encodePath(body.target_type)}/${encodePath(body.target_id)}/`, { method: 'DELETE' }),
};

export const communityNotificationsApi = {
  list: (query: CommunityNotificationListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<CursorPage<CommunityNotification>>('/api/v1/community/me/notifications/', {
      ...context,
      decode: (value) => decodeCursorPage(value, decodeCommunityNotification),
      query,
    }),
  unreadCount: (context: ApiRequestContext = {}) =>
    api.get<CommunityNotificationUnreadCount>('/api/v1/community/me/notifications/unread-count/', {
      ...context,
      decode: decodeNotificationUnreadCount,
    }),
  markRead: (notificationId: number) =>
    api.put<CommunityNotification>(`/api/v1/community/me/notifications/${encodePath(notificationId)}/read-state/`, undefined, {
      decode: decodeCommunityNotification,
    }),
  markAllRead: () =>
    api.put<CommunityNotificationReadAllResult>('/api/v1/community/me/notifications/read-state/', undefined, {
      decode: decodeNotificationReadAllResult,
    }),
};

export const communityReportsApi = {
  create: (body: {
    target_type: CommunityTargetType;
    target_id: number;
    reason: CommunityReportReason;
    description?: string;
  }) => api.post<CommunityReport, typeof body>('/api/v1/community/reports/', body, { decode: decodeCommunityReport }),
  listMine: (query: CommunityReportListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityReport>>('/api/v1/community/me/reports/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityReport),
      query,
    }),
  listStaff: (query: CommunityReportListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CommunityReport>>('/api/v1/community/moderation/reports/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCommunityReport),
      query,
    }),
  resolve: (
    reportId: number,
    body: { status: CommunityReportStatus; action_type?: string; moderation_reason?: string },
  ) =>
    api.patch<CommunityReport, typeof body>(`/api/v1/community/moderation/reports/${encodePath(reportId)}/`, body, {
      decode: decodeCommunityReport,
    }),
};
