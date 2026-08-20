import {
  api,
  decodeApiPage,
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

  listCollections: async (_userId: number, _query: PublicCollectionListQuery = {}, _context: ApiRequestContext = {}) =>
    ({
      count: 0,
      next: null,
      previous: null,
      results: [] as Collection[],
    }) satisfies ApiPage<Collection>,

  getCollection: async (_userId: number, _collectionId: number, _context: ApiRequestContext = {}) =>
    ({
      id: 0,
      name: '',
      simple_rating: null,
      note: '',
      is_public: true,
      item_count: 0,
      reaction_count: 0,
    }) as Collection,

  listCollectionItems: async (
    _userId: number,
    _collectionId: number,
    _query: PageQuery = {},
    _context: ApiRequestContext = {},
  ) =>
    ({
      count: 0,
      next: null,
      previous: null,
      results: [] as CollectionItem[],
    }) satisfies ApiPage<CollectionItem>,
};
