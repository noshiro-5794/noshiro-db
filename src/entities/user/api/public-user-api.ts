import {
  api,
  decodeApiPage,
  decodeCollectionItem,
  decodePublicCollection,
  decodePublicReview,
  decodePublicUserSubject,
  encodePath,
} from '@/shared/api';
import type {
  ApiPage,
  ApiRequestContext,
  Collection,
  CollectionItem,
  PageQuery,
  PrimarySubjectType,
  PublicUserProfile,
  Review,
  UserSubject,
  UserSubjectStatus,
} from '@/shared/api';
import { decodePublicUserProfile } from './public-user-decoders';

export type PublicSubjectListQuery = PageQuery & {
  status?: UserSubjectStatus;
  subject_type?: PrimarySubjectType;
  keyword?: string;
  tag_id?: number;
  ordering?:
    | 'id'
    | '-id'
    | 'simple_rating'
    | '-simple_rating'
    | 'rating'
    | '-rating'
    | 'watch_start_date'
    | '-watch_start_date'
    | 'watch_end_date'
    | '-watch_end_date';
};

export type PublicReviewListQuery = PageQuery & {
  keyword?: string;
  ordering?: 'created_at' | '-created_at' | 'id' | '-id';
};

export type PublicCollectionListQuery = PageQuery & {
  keyword?: string;
  ordering?: 'id' | '-id' | 'name' | '-name' | 'simple_rating' | '-simple_rating' | 'item_count' | '-item_count';
};

export const publicUsersApi = {
  getProfile: (userId: number, context: ApiRequestContext = {}) =>
    api.get<PublicUserProfile>(`/api/users/${encodePath(userId)}/profile/`, {
      ...context,
      decode: decodePublicUserProfile,
    }),

  listSubjects: (userId: number, query: PublicSubjectListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<UserSubject>>(`/api/users/${encodePath(userId)}/subjects/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodePublicUserSubject),
      query,
    }),

  listReviews: (userId: number, query: PublicReviewListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Review>>(`/api/users/${encodePath(userId)}/reviews/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodePublicReview),
      query,
    }),

  listCollections: (userId: number, query: PublicCollectionListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Collection>>(`/api/users/${encodePath(userId)}/collections/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodePublicCollection),
      query,
    }),

  getCollection: (userId: number, collectionId: number, context: ApiRequestContext = {}) =>
    api.get<Collection>(`/api/users/${encodePath(userId)}/collections/${encodePath(collectionId)}/`, {
      ...context,
      decode: decodePublicCollection,
    }),

  listCollectionItems: (userId: number, collectionId: number, query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CollectionItem>>(
      `/api/users/${encodePath(userId)}/collections/${encodePath(collectionId)}/items/`,
      { ...context, decode: (value) => decodeApiPage(value, decodeCollectionItem), query },
    ),
};
