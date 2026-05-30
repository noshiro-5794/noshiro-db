import { mutationOptions, queryOptions } from '@tanstack/react-query';
import {
  activitiesApi,
  followsApi,
  publicUsersApi,
  type ActivityListQuery,
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
  follows: () => [...socialQueryKeys.all, 'follows'] as const,
  myFollowing: () => [...socialQueryKeys.follows(), 'my-following'] as const,
  myFollowers: () => [...socialQueryKeys.follows(), 'my-followers'] as const,
  publicFollowing: (userId: number) => [...socialQueryKeys.follows(), userId, 'following'] as const,
  publicFollowers: (userId: number) => [...socialQueryKeys.follows(), userId, 'followers'] as const,
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

  myFollowing: () =>
    queryOptions({
      queryKey: socialQueryKeys.myFollowing(),
      queryFn: () => followsApi.listMyFollowing(),
    }),

  myFollowers: () =>
    queryOptions({
      queryKey: socialQueryKeys.myFollowers(),
      queryFn: () => followsApi.listMyFollowers(),
    }),

  publicFollowing: (userId: number) =>
    queryOptions({
      queryKey: socialQueryKeys.publicFollowing(userId),
      queryFn: () => followsApi.listPublicFollowing(userId),
    }),

  publicFollowers: (userId: number) =>
    queryOptions({
      queryKey: socialQueryKeys.publicFollowers(userId),
      queryFn: () => followsApi.listPublicFollowers(userId),
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
