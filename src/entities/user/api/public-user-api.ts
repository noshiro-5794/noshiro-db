import {
  api,
  decodeApiPage,
  decodeCollection,
  decodeCollectionItem,
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
    api.get<PublicUserProfile>(`/api/v1/users/${encodePath(userId)}/`, {
      ...context,
      decode: decodePublicUserProfile,
    }),

  listSubjects: (userId: number, query: PublicSubjectListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<UserSubject>>(`/api/v1/users/${encodePath(userId)}/library/entries/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodePublicUserSubject),
      query: {
        ...(query.subject_type === undefined ? {} : { subject_type: query.subject_type }),
        ...(query.keyword === undefined ? {} : { keyword: query.keyword }),
        ...(query.ordering === undefined ? {} : { ordering: query.ordering }),
        ...(query.page === undefined ? {} : { page: query.page }),
        ...(query.page_size === undefined ? {} : { page_size: query.page_size }),
        ...(query.status === undefined ? {} : { status: query.status }),
      },
    }),

  listReviews: (userId: number, query: PublicReviewListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Review>>(`/api/v1/users/${encodePath(userId)}/reviews/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodePublicReview),
      query: {
        ...(query.keyword ? { query: query.keyword } : {}),
        ...(query.page === undefined ? {} : { page: query.page }),
        ...(query.page_size === undefined ? {} : { page_size: query.page_size }),
      },
    }),

  listCollections: (userId: number, query: PublicCollectionListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Collection>>(`/api/v1/users/${encodePath(userId)}/collections/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCollection),
      query: {
        ...(query.keyword ? { keyword: query.keyword } : {}),
        ...(query.ordering ? { ordering: query.ordering } : {}),
        ...(query.page === undefined ? {} : { page: query.page }),
        ...(query.page_size === undefined ? {} : { page_size: query.page_size }),
      },
    }),

  getCollection: (userId: number, collectionId: number, context: ApiRequestContext = {}) =>
    api.get<Collection>(`/api/v1/users/${encodePath(userId)}/collections/${encodePath(collectionId)}/`, {
      ...context,
      decode: decodeCollection,
    }),

  listCollectionItems: (userId: number, collectionId: number, query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CollectionItem>>(
      `/api/v1/users/${encodePath(userId)}/collections/${encodePath(collectionId)}/items/`,
      {
        ...context,
        decode: (value) => decodeApiPage(value, decodeCollectionItem),
        query: {
          ...(query.page === undefined ? {} : { page: query.page }),
          ...(query.page_size === undefined ? {} : { page_size: query.page_size }),
        },
      },
    ),
};
