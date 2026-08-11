import { queryOptions } from '@tanstack/react-query';
import {
  publicUsersApi,
  type PublicCollectionListQuery,
  type PublicReviewListQuery,
  type PublicSubjectListQuery,
} from '../api/public-user-api';
import type { PageQuery } from '@/shared/api';

export const publicUserQueryKeys = {
  all: ['public-users'] as const,
  user: (userId: number) => [...publicUserQueryKeys.all, userId] as const,
  publicProfile: (userId: number) => [...publicUserQueryKeys.user(userId), 'profile'] as const,
  publicSubjects: (userId: number, query: PublicSubjectListQuery = {}) =>
    [...publicUserQueryKeys.user(userId), 'subjects', query] as const,
  publicReviews: (userId: number, query: PublicReviewListQuery = {}) =>
    [...publicUserQueryKeys.user(userId), 'reviews', query] as const,
  publicCollections: (userId: number, query: PublicCollectionListQuery = {}) =>
    [...publicUserQueryKeys.user(userId), 'collections', query] as const,
  publicCollection: (userId: number, collectionId: number) =>
    [...publicUserQueryKeys.user(userId), 'collections', collectionId] as const,
  publicCollectionItems: (userId: number, collectionId: number, query: PageQuery = {}) =>
    [...publicUserQueryKeys.user(userId), 'collections', collectionId, 'items', query] as const,
};

export const publicUserQueries = {
  publicProfile: (userId: number) =>
    queryOptions({
      queryKey: publicUserQueryKeys.publicProfile(userId),
      queryFn: ({ signal }) => publicUsersApi.getProfile(userId, { signal }),
    }),

  publicSubjects: (userId: number, query: PublicSubjectListQuery = {}) =>
    queryOptions({
      queryKey: publicUserQueryKeys.publicSubjects(userId, query),
      queryFn: ({ signal }) => publicUsersApi.listSubjects(userId, query, { signal }),
    }),

  publicReviews: (userId: number, query: PublicReviewListQuery = {}) =>
    queryOptions({
      queryKey: publicUserQueryKeys.publicReviews(userId, query),
      queryFn: ({ signal }) => publicUsersApi.listReviews(userId, query, { signal }),
    }),

  publicCollections: (userId: number, query: PublicCollectionListQuery = {}) =>
    queryOptions({
      queryKey: publicUserQueryKeys.publicCollections(userId, query),
      queryFn: ({ signal }) => publicUsersApi.listCollections(userId, query, { signal }),
    }),

  publicCollection: (userId: number, collectionId: number) =>
    queryOptions({
      queryKey: publicUserQueryKeys.publicCollection(userId, collectionId),
      queryFn: ({ signal }) => publicUsersApi.getCollection(userId, collectionId, { signal }),
    }),

  publicCollectionItems: (userId: number, collectionId: number, query: PageQuery = {}) =>
    queryOptions({
      queryKey: publicUserQueryKeys.publicCollectionItems(userId, collectionId, query),
      queryFn: ({ signal }) => publicUsersApi.listCollectionItems(userId, collectionId, query, { signal }),
    }),
};
