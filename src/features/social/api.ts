import { api } from '@/lib/api/client';
import { encodePath } from '@/lib/api/path';
import type { Activity, ActivityType, ApiPage, Collection, FollowRelation, PublicUserProfile, Review, UserSubject } from '@/lib/api/types';
import type { CollectionListQuery, ReviewListQuery, UserSubjectListQuery } from '@/features/library/api';

export type ActivityListQuery = {
  page?: number;
  page_size?: number;
  activity_type?: ActivityType;
  ordering?: 'id' | '-id' | 'created_at' | '-created_at';
  include_self?: boolean;
};

export const followsApi = {
  follow: (targetUserId: number) => api.post<FollowRelation>(`/api/users/me/following/${encodePath(targetUserId)}/`),

  listMyFollowing: (query: { page?: number; page_size?: number } = {}) => api.get<ApiPage<FollowRelation>>('/api/users/me/following/', { query }),

  listMyFollowers: (query: { page?: number; page_size?: number } = {}) => api.get<ApiPage<FollowRelation>>('/api/users/me/followers/', { query }),

  listPublicFollowing: (userId: number, query: { page?: number; page_size?: number } = {}) =>
    api.get<ApiPage<FollowRelation>>(`/api/users/${encodePath(userId)}/following/`, { query, skipAuth: true }),

  listPublicFollowers: (userId: number, query: { page?: number; page_size?: number } = {}) =>
    api.get<ApiPage<FollowRelation>>(`/api/users/${encodePath(userId)}/followers/`, { query, skipAuth: true }),

  unfollow: (targetUserId: number) => api.delete<unknown>(`/api/users/me/following/${encodePath(targetUserId)}/`),
};

export const publicUsersApi = {
  getProfile: (userId: number) => api.get<PublicUserProfile>(`/api/users/${encodePath(userId)}/profile/`),

  listSubjects: (userId: number, query: UserSubjectListQuery = {}) =>
    api.get<ApiPage<UserSubject>>(`/api/users/${encodePath(userId)}/subjects/`, { query }),

  listReviews: (userId: number, query: ReviewListQuery = {}) =>
    api.get<ApiPage<Review>>(`/api/users/${encodePath(userId)}/reviews/`, { query, skipAuth: true }),

  listCollections: (userId: number, query: CollectionListQuery = {}) =>
    api.get<ApiPage<Collection>>(`/api/users/${encodePath(userId)}/collections/`, { query, skipAuth: true }),
};

export const activitiesApi = {
  listMine: (query: ActivityListQuery = {}) => api.get<ApiPage<Activity>>('/api/users/me/activities/', { query }),

  listPublic: (userId: number, query: ActivityListQuery = {}) =>
    api.get<ApiPage<Activity>>(`/api/users/${encodePath(userId)}/activities/`, { query, skipAuth: true }),

  listFeed: (query: ActivityListQuery = {}) => api.get<ApiPage<Activity>>('/api/users/me/feed/', { query }),
};
