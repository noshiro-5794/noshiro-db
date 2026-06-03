import { mutationOptions, queryOptions } from '@tanstack/react-query';
import {
  activitiesApi,
  followsApi,
  publicUsersApi,
  type ActivityListQuery,
  type FollowListQuery,
} from '@/features/social/api';
import type { CollectionListQuery, ReviewListQuery, UserSubjectListQuery } from '@/features/library/api';

export const socialQueryKeys = {
  all: ['social'] as const,
  publicUsers: () => [...socialQueryKeys.all, 'public-users'] as const,
  publicProfile: (userId: number) => [...socialQueryKeys.publicUsers(), userId, 'profile'] as const,
  publicSubjects: (userId: number, query: UserSubjectListQuery = {}) =>
    [...socialQueryKeys.publicUsers(), userId, 'subjects', query] as const,
  publicReviews: (userId: number, query: ReviewListQuery = {}) => [...socialQueryKeys.publicUsers(), userId, 'reviews', query] as const,
  publicCollections: (userId: number, query: CollectionListQuery = {}) =>
    [...socialQueryKeys.publicUsers(), userId, 'collections', query] as const,
  publicCollection: (userId: number, collectionId: number) =>
    [...socialQueryKeys.publicUsers(), userId, 'collections', collectionId] as const,
  publicCollectionItems: (userId: number, collectionId: number, query: FollowListQuery = {}) =>
    [...socialQueryKeys.publicUsers(), userId, 'collections', collectionId, 'items', query] as const,
  follows: () => [...socialQueryKeys.all, 'follows'] as const,
  myFollowing: (query: FollowListQuery = {}) => [...socialQueryKeys.follows(), 'my-following', query] as const,
  myFollowers: (query: FollowListQuery = {}) => [...socialQueryKeys.follows(), 'my-followers', query] as const,
  publicFollowing: (userId: number, query: FollowListQuery = {}) => [...socialQueryKeys.follows(), userId, 'following', query] as const,
  publicFollowers: (userId: number, query: FollowListQuery = {}) => [...socialQueryKeys.follows(), userId, 'followers', query] as const,
  activities: () => [...socialQueryKeys.all, 'activities'] as const,
  myActivities: (query: ActivityListQuery = {}) => [...socialQueryKeys.activities(), 'mine', query] as const,
  publicActivities: (userId: number, query: ActivityListQuery = {}) => [...socialQueryKeys.activities(), 'public', userId, query] as const,
  feed: (query: ActivityListQuery = {}) => [...socialQueryKeys.activities(), 'feed', query] as const,
};

export const socialQueries = {
  publicProfile: (userId: number) =>
    queryOptions({
      queryKey: socialQueryKeys.publicProfile(userId),
      queryFn: () => publicUsersApi.getProfile(userId),
    }),

  publicSubjects: (userId: number, query: UserSubjectListQuery = {}) =>
    queryOptions({
      queryKey: socialQueryKeys.publicSubjects(userId, query),
      queryFn: () => publicUsersApi.listSubjects(userId, query),
    }),

  publicReviews: (userId: number, query: ReviewListQuery = {}) =>
    queryOptions({
      queryKey: socialQueryKeys.publicReviews(userId, query),
      queryFn: () => publicUsersApi.listReviews(userId, query),
    }),

  publicCollections: (userId: number, query: CollectionListQuery = {}) =>
    queryOptions({
      queryKey: socialQueryKeys.publicCollections(userId, query),
      queryFn: () => publicUsersApi.listCollections(userId, query),
    }),

  publicCollection: (userId: number, collectionId: number) =>
    queryOptions({
      queryKey: socialQueryKeys.publicCollection(userId, collectionId),
      queryFn: () => publicUsersApi.getCollection(userId, collectionId),
    }),

  publicCollectionItems: (userId: number, collectionId: number, query: FollowListQuery = {}) =>
    queryOptions({
      queryKey: socialQueryKeys.publicCollectionItems(userId, collectionId, query),
      queryFn: () => publicUsersApi.listCollectionItems(userId, collectionId, query),
    }),

  myFollowing: (query: FollowListQuery = {}) =>
    queryOptions({
      queryKey: socialQueryKeys.myFollowing(query),
      queryFn: () => followsApi.listMyFollowing(query),
    }),

  myFollowers: (query: FollowListQuery = {}) =>
    queryOptions({
      queryKey: socialQueryKeys.myFollowers(query),
      queryFn: () => followsApi.listMyFollowers(query),
    }),

  publicFollowing: (userId: number, query: FollowListQuery = {}) =>
    queryOptions({
      queryKey: socialQueryKeys.publicFollowing(userId, query),
      queryFn: () => followsApi.listPublicFollowing(userId, query),
    }),

  publicFollowers: (userId: number, query: FollowListQuery = {}) =>
    queryOptions({
      queryKey: socialQueryKeys.publicFollowers(userId, query),
      queryFn: () => followsApi.listPublicFollowers(userId, query),
    }),

  myActivities: (query: ActivityListQuery = {}) =>
    queryOptions({
      queryKey: socialQueryKeys.myActivities(query),
      queryFn: () => activitiesApi.listMine(query),
    }),

  publicActivities: (userId: number, query: ActivityListQuery = {}) =>
    queryOptions({
      queryKey: socialQueryKeys.publicActivities(userId, query),
      queryFn: () => activitiesApi.listPublic(userId, query),
    }),

  feed: (query: ActivityListQuery = {}) =>
    queryOptions({
      queryKey: socialQueryKeys.feed(query),
      queryFn: () => activitiesApi.listFeed(query),
    }),
};

export const socialMutations = {
  follow: () =>
    mutationOptions({
      mutationFn: (targetUserId: number) => followsApi.follow(targetUserId),
    }),

  unfollow: () =>
    mutationOptions({
      mutationFn: (targetUserId: number) => followsApi.unfollow(targetUserId),
    }),
};
