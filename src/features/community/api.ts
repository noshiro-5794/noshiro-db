import { api, apiRequest } from '@/lib/api/client';
import { encodePath } from '@/lib/api/path';
import type {
  Activity,
  ActivityType,
  ApiPage,
  CommunityBookmark,
  CommunityCommentSummary,
  CommunityNotification,
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
} from '@/lib/api/types';

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
  ordering?: '-last_activity_at' | 'last_activity_at' | '-created_at' | 'created_at' | '-reaction_count' | 'reaction_count' | '-reply_count' | 'reply_count';
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
  follow: (targetUserId: number) => api.post<FollowRelation>(`/api/community/me/following/${encodePath(targetUserId)}/`),
  unfollow: (targetUserId: number) => api.delete<unknown>(`/api/community/me/following/${encodePath(targetUserId)}/`),
  listMyFollowing: (query: PageQuery = {}) => api.get<ApiPage<FollowRelation>>('/api/community/me/following/', { query }),
  listMyFollowers: (query: PageQuery = {}) => api.get<ApiPage<FollowRelation>>('/api/community/me/followers/', { query }),
  listUserFollowing: (userId: number, query: PageQuery = {}) =>
    api.get<ApiPage<FollowRelation>>(`/api/community/users/${encodePath(userId)}/following/`, { query }),
  listUserFollowers: (userId: number, query: PageQuery = {}) =>
    api.get<ApiPage<FollowRelation>>(`/api/community/users/${encodePath(userId)}/followers/`, { query }),
};

export const communityRelationshipsApi = {
  listBlocks: (query: PageQuery = {}) => api.get<ApiPage<CommunityRelationship>>('/api/community/me/blocks/', { query }),
  block: (targetUserId: number, body: { reason?: string } = {}) =>
    api.post<CommunityRelationship, typeof body>(`/api/community/me/blocks/${encodePath(targetUserId)}/`, body),
  unblock: (targetUserId: number) => api.delete<unknown>(`/api/community/me/blocks/${encodePath(targetUserId)}/`),
  listMutes: (query: PageQuery = {}) => api.get<ApiPage<CommunityRelationship>>('/api/community/me/mutes/', { query }),
  mute: (targetUserId: number, body: { reason?: string } = {}) =>
    api.post<CommunityRelationship, typeof body>(`/api/community/me/mutes/${encodePath(targetUserId)}/`, body),
  unmute: (targetUserId: number) => api.delete<unknown>(`/api/community/me/mutes/${encodePath(targetUserId)}/`),
};

export const communityActivitiesApi = {
  listPublic: (query: CommunityActivityListQuery = {}) => api.get<ApiPage<Activity>>('/api/community/activities/', { query }),
  listMine: (query: CommunityActivityListQuery = {}) => api.get<ApiPage<Activity>>('/api/community/me/activities/', { query }),
  listFeed: (query: CommunityActivityListQuery = {}) => api.get<ApiPage<Activity>>('/api/community/me/feed/', { query }),
  listUser: (userId: number, query: CommunityActivityListQuery = {}) =>
    api.get<ApiPage<Activity>>(`/api/community/users/${encodePath(userId)}/activities/`, { query }),
};

export const communityPostsApi = {
  list: (query: CommunityPostListQuery = {}) => api.get<ApiPage<CommunityPostSummary>>('/api/community/posts/', { query }),
  create: (body: CommunityPostBody) => api.post<CommunityPostSummary, CommunityPostBody>('/api/community/posts/', body),
  get: (postId: number) => api.get<CommunityPostSummary>(`/api/community/posts/${encodePath(postId)}/`),
  update: (postId: number, body: Partial<CommunityPostBody>) =>
    api.patch<CommunityPostSummary, Partial<CommunityPostBody>>(`/api/community/posts/${encodePath(postId)}/`, body),
  delete: (postId: number) => api.delete<unknown>(`/api/community/posts/${encodePath(postId)}/`),
  listComments: (postId: number, query: PageQuery = {}) =>
    api.get<ApiPage<CommunityCommentSummary>>(`/api/community/posts/${encodePath(postId)}/comments/`, { query }),
  createComment: (postId: number, body: Omit<CommunityCommentBody, 'target_type' | 'target_id'>) =>
    api.post<CommunityCommentSummary, typeof body>(`/api/community/posts/${encodePath(postId)}/comments/`, body),
};

export const communityCommentsApi = {
  list: (query: CommunityCommentListQuery) => api.get<ApiPage<CommunityCommentSummary>>('/api/community/comments/', { query }),
  create: (body: CommunityCommentBody & { target_type: CommunityTargetType; target_id: number }) =>
    api.post<CommunityCommentSummary, typeof body>('/api/community/comments/', body),
  update: (commentId: number, body: Partial<Pick<CommunityCommentBody, 'content' | 'visibility' | 'is_spoiler'>>) =>
    api.patch<CommunityCommentSummary, typeof body>(`/api/community/comments/${encodePath(commentId)}/`, body),
  delete: (commentId: number) => api.delete<unknown>(`/api/community/comments/${encodePath(commentId)}/`),
};

export const communityInteractionsApi = {
  react: (body: { target_type: CommunityTargetType; target_id: number; reaction_type?: CommunityReactionType }) =>
    api.post<CommunityReaction, typeof body>('/api/community/reactions/', body),
  unreact: (body: { target_type: CommunityTargetType; target_id: number; reaction_type?: CommunityReactionType }) =>
    apiRequest<unknown, typeof body>('/api/community/reactions/', { method: 'DELETE', body }),
  listBookmarks: (query: CommunityBookmarkListQuery = {}) => api.get<ApiPage<CommunityBookmark>>('/api/community/bookmarks/', { query }),
  bookmark: (body: { target_type: CommunityTargetType; target_id: number }) =>
    api.post<CommunityBookmark, typeof body>('/api/community/bookmarks/', body),
  unbookmark: (body: { target_type: CommunityTargetType; target_id: number }) =>
    apiRequest<unknown, typeof body>('/api/community/bookmarks/', { method: 'DELETE', body }),
};

export const communityNotificationsApi = {
  list: (query: CommunityNotificationListQuery = {}) => api.get<ApiPage<CommunityNotification>>('/api/community/notifications/', { query }),
  unreadCount: () => api.get<CommunityNotificationUnreadCount>('/api/community/notifications/unread-count/'),
  markRead: (notificationId: number) => api.patch<CommunityNotification>(`/api/community/notifications/${encodePath(notificationId)}/read/`),
  markAllRead: () => api.post<CommunityNotificationUnreadCount>('/api/community/notifications/read-all/'),
};

export const communityReportsApi = {
  create: (body: { target_type: CommunityTargetType; target_id: number; reason: CommunityReportReason; description?: string }) =>
    api.post<CommunityReport, typeof body>('/api/community/reports/', body),
  listMine: (query: CommunityReportListQuery = {}) => api.get<ApiPage<CommunityReport>>('/api/community/me/reports/', { query }),
  listStaff: (query: CommunityReportListQuery = {}) => api.get<ApiPage<CommunityReport>>('/api/community/staff/reports/', { query }),
  resolve: (reportId: number, body: { status: CommunityReportStatus; action_type?: string; moderation_reason?: string }) =>
    api.patch<CommunityReport, typeof body>(`/api/community/staff/reports/${encodePath(reportId)}/resolve/`, body),
};
