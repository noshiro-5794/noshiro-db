import { api } from '@/lib/api/client';
import { encodePath } from '@/lib/api/path';
import type { Activity, ActivityType, ApiPage, Collection, CollectionItem, FollowRelation, PublicUserProfile, Review, UserSubject } from '@/lib/api/types';
import type { CollectionListQuery, ReviewListQuery, UserSubjectListQuery } from '@/features/library/api';

export type ActivityListQuery = {
  page?: number;
  page_size?: number;
  activity_type?: ActivityType;
  ordering?: 'id' | '-id' | 'created_at' | '-created_at';
  include_self?: boolean;
};

export type FollowListQuery = {
  page?: number;
  page_size?: number;
};

export const followsApi = {
  follow: (targetUserId: number) => api.post<FollowRelation>(`/api/community/me/following/${encodePath(targetUserId)}/`),

  listMyFollowing: (query: FollowListQuery = {}) => api.get<ApiPage<FollowRelation>>('/api/community/me/following/', { query }),

  listMyFollowers: (query: FollowListQuery = {}) => api.get<ApiPage<FollowRelation>>('/api/community/me/followers/', { query }),

  listPublicFollowing: (userId: number, query: FollowListQuery = {}) =>
    api.get<ApiPage<FollowRelation>>(`/api/community/users/${encodePath(userId)}/following/`, { query }),

  listPublicFollowers: (userId: number, query: FollowListQuery = {}) =>
    api.get<ApiPage<FollowRelation>>(`/api/community/users/${encodePath(userId)}/followers/`, { query }),

  unfollow: (targetUserId: number) => api.delete<unknown>(`/api/community/me/following/${encodePath(targetUserId)}/`),
};

export const publicUsersApi = {
  getProfile: (userId: number) => api.get<PublicUserProfile>(`/api/users/${encodePath(userId)}/profile/`),

  listSubjects: (userId: number, query: UserSubjectListQuery = {}) =>
    api.get<ApiPage<UserSubject>>(`/api/users/${encodePath(userId)}/subjects/`, { query }),

  listReviews: (userId: number, query: ReviewListQuery = {}) =>
    api.get<ApiPage<Review>>(`/api/users/${encodePath(userId)}/reviews/`, { query }),

  listCollections: (userId: number, query: CollectionListQuery = {}) =>
    api.get<ApiPage<Collection>>(`/api/users/${encodePath(userId)}/collections/`, { query }),

  getCollection: (userId: number, collectionId: number) =>
    api.get<Collection>(`/api/users/${encodePath(userId)}/collections/${encodePath(collectionId)}/`),

  listCollectionItems: (userId: number, collectionId: number, query: { page?: number; page_size?: number } = {}) =>
    api.get<ApiPage<CollectionItem>>(`/api/users/${encodePath(userId)}/collections/${encodePath(collectionId)}/items/`, { query }),
};

export const activitiesApi = {
  listMine: (query: ActivityListQuery = {}) => api.get<ApiPage<Activity>>('/api/community/me/activities/', { query }),

  listPublic: (userId: number, query: ActivityListQuery = {}) =>
    api.get<ApiPage<Activity>>(`/api/community/users/${encodePath(userId)}/activities/`, { query }),

  listFeed: (query: ActivityListQuery = {}) => api.get<ApiPage<Activity>>('/api/community/me/feed/', { query }),
};
