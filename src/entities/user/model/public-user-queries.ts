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
  publicProfile: (userId: number) => [...publicUserQueryKeys.all, userId, 'profile'] as const,
  publicSubjects: (userId: number, query: PublicSubjectListQuery = {}) =>
    [...publicUserQueryKeys.all, userId, 'subjects', query] as const,
  publicReviews: (userId: number, query: PublicReviewListQuery = {}) =>
    [...publicUserQueryKeys.all, userId, 'reviews', query] as const,
  publicCollections: (userId: number, query: PublicCollectionListQuery = {}) =>
    [...publicUserQueryKeys.all, userId, 'collections', query] as const,
  publicCollection: (userId: number, collectionId: number) =>
    [...publicUserQueryKeys.all, userId, 'collections', collectionId] as const,
  publicCollectionItems: (userId: number, collectionId: number, query: PageQuery = {}) =>
    [...publicUserQueryKeys.all, userId, 'collections', collectionId, 'items', query] as const,
};

export const publicUserQueries = {
  publicProfile: (userId: number) =>
    queryOptions({
      queryKey: publicUserQueryKeys.publicProfile(userId),
      queryFn: () => publicUsersApi.getProfile(userId),
    }),

  publicSubjects: (userId: number, query: PublicSubjectListQuery = {}) =>
    queryOptions({
      queryKey: publicUserQueryKeys.publicSubjects(userId, query),
      queryFn: () => publicUsersApi.listSubjects(userId, query),
    }),

  publicReviews: (userId: number, query: PublicReviewListQuery = {}) =>
    queryOptions({
      queryKey: publicUserQueryKeys.publicReviews(userId, query),
      queryFn: () => publicUsersApi.listReviews(userId, query),
    }),

  publicCollections: (userId: number, query: PublicCollectionListQuery = {}) =>
    queryOptions({
      queryKey: publicUserQueryKeys.publicCollections(userId, query),
      queryFn: () => publicUsersApi.listCollections(userId, query),
    }),

  publicCollection: (userId: number, collectionId: number) =>
    queryOptions({
      queryKey: publicUserQueryKeys.publicCollection(userId, collectionId),
      queryFn: () => publicUsersApi.getCollection(userId, collectionId),
    }),

  publicCollectionItems: (userId: number, collectionId: number, query: PageQuery = {}) =>
    queryOptions({
      queryKey: publicUserQueryKeys.publicCollectionItems(userId, collectionId, query),
      queryFn: () => publicUsersApi.listCollectionItems(userId, collectionId, query),
    }),
};
