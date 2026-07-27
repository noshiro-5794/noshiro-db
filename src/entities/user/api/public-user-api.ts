import { api } from '@/shared/api';
import { encodePath } from '@/shared/api';
import type {
  ApiPage,
  Collection,
  CollectionItem,
  PageQuery,
  PrimarySubjectType,
  PublicUserProfile,
  Review,
  UserSubject,
  UserSubjectStatus,
} from '@/shared/api';

export type PublicSubjectListQuery = PageQuery & {
  status?: UserSubjectStatus;
  subject_type?: PrimarySubjectType;
  keyword?: string;
  tag_id?: number;
  ordering?: string;
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
  getProfile: (userId: number) => api.get<PublicUserProfile>(`/api/users/${encodePath(userId)}/profile/`),

  listSubjects: (userId: number, query: PublicSubjectListQuery = {}) =>
    api.get<ApiPage<UserSubject>>(`/api/users/${encodePath(userId)}/subjects/`, { query }),

  listReviews: (userId: number, query: PublicReviewListQuery = {}) =>
    api.get<ApiPage<Review>>(`/api/users/${encodePath(userId)}/reviews/`, { query }),

  listCollections: (userId: number, query: PublicCollectionListQuery = {}) =>
    api.get<ApiPage<Collection>>(`/api/users/${encodePath(userId)}/collections/`, { query }),

  getCollection: (userId: number, collectionId: number) =>
    api.get<Collection>(`/api/users/${encodePath(userId)}/collections/${encodePath(collectionId)}/`),

  listCollectionItems: (userId: number, collectionId: number, query: PageQuery = {}) =>
    api.get<ApiPage<CollectionItem>>(
      `/api/users/${encodePath(userId)}/collections/${encodePath(collectionId)}/items/`,
      { query },
    ),
};
