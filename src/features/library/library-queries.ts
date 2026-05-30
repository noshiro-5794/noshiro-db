import { mutationOptions, queryOptions } from '@tanstack/react-query';
import {
  collectionsApi,
  progressApi,
  ratingDetailsApi,
  reviewsApi,
  tagsApi,
  userSubjectsApi,
  type CollectionListQuery,
  type CreateUserSubjectBody,
  type ReviewListQuery,
  type UserSubjectListQuery,
} from '@/features/library/api';
import type { RatingDetail, Review, UUID, UserSubject } from '@/lib/api/types';

export const libraryQueryKeys = {
  all: ['library'] as const,
  userSubjects: () => [...libraryQueryKeys.all, 'user-subjects'] as const,
  userSubjectList: (query: UserSubjectListQuery = {}) => [...libraryQueryKeys.userSubjects(), 'list', query] as const,
  userSubjectDetail: (userSubjectId: number) => [...libraryQueryKeys.userSubjects(), 'detail', userSubjectId] as const,
  subjectContext: (subjectId: UUID) => [...libraryQueryKeys.userSubjects(), 'context', subjectId] as const,
  progress: (subjectId: UUID) => [...libraryQueryKeys.all, 'progress', subjectId] as const,
  tags: () => [...libraryQueryKeys.all, 'tags'] as const,
  tagList: () => [...libraryQueryKeys.tags(), 'list'] as const,
  subjectTags: (subjectId: UUID) => [...libraryQueryKeys.tags(), 'subject', subjectId] as const,
  ratingDetails: (subjectId: UUID) => [...libraryQueryKeys.all, 'rating-details', subjectId] as const,
  reviews: () => [...libraryQueryKeys.all, 'reviews'] as const,
  reviewList: (query: ReviewListQuery = {}) => [...libraryQueryKeys.reviews(), 'list', query] as const,
  subjectReviews: (subjectId: UUID) => [...libraryQueryKeys.reviews(), 'subject', subjectId] as const,
  reviewDetail: (reviewId: number) => [...libraryQueryKeys.reviews(), 'detail', reviewId] as const,
  collections: () => [...libraryQueryKeys.all, 'collections'] as const,
  collectionList: (query: CollectionListQuery = {}) => [...libraryQueryKeys.collections(), 'list', query] as const,
  collectionDetail: (collectionId: number) => [...libraryQueryKeys.collections(), 'detail', collectionId] as const,
  collectionItems: (collectionId: number) => [...libraryQueryKeys.collections(), 'items', collectionId] as const,
};

export const libraryQueries = {
  userSubjects: (query: UserSubjectListQuery = {}) =>
    queryOptions({
      queryKey: libraryQueryKeys.userSubjectList(query),
      queryFn: () => userSubjectsApi.listMine(query),
    }),

  userSubject: (userSubjectId: number) =>
    queryOptions({
      queryKey: libraryQueryKeys.userSubjectDetail(userSubjectId),
      queryFn: () => userSubjectsApi.getMine(userSubjectId),
    }),

  subjectContext: (subjectId: UUID) =>
    queryOptions({
      queryKey: libraryQueryKeys.subjectContext(subjectId),
      queryFn: () => userSubjectsApi.getContext(subjectId),
    }),

  progress: (subjectId: UUID) =>
    queryOptions({
      queryKey: libraryQueryKeys.progress(subjectId),
      queryFn: () => progressApi.get(subjectId),
    }),

  tags: () =>
    queryOptions({
      queryKey: libraryQueryKeys.tagList(),
      queryFn: () => tagsApi.listMine(),
    }),

  subjectTags: (subjectId: UUID) =>
    queryOptions({
      queryKey: libraryQueryKeys.subjectTags(subjectId),
      queryFn: () => tagsApi.getForSubject(subjectId),
    }),

  ratingDetails: (subjectId: UUID) =>
    queryOptions({
      queryKey: libraryQueryKeys.ratingDetails(subjectId),
      queryFn: () => ratingDetailsApi.getForSubject(subjectId),
    }),

  reviews: (query: ReviewListQuery = {}) =>
    queryOptions({
      queryKey: libraryQueryKeys.reviewList(query),
      queryFn: () => reviewsApi.listMine(query),
    }),

  subjectReviews: (subjectId: UUID) =>
    queryOptions({
      queryKey: libraryQueryKeys.subjectReviews(subjectId),
      queryFn: () => reviewsApi.listForSubject(subjectId),
    }),

  review: (reviewId: number) =>
    queryOptions({
      queryKey: libraryQueryKeys.reviewDetail(reviewId),
      queryFn: () => reviewsApi.getMine(reviewId),
    }),

  collections: (query: CollectionListQuery = {}) =>
    queryOptions({
      queryKey: libraryQueryKeys.collectionList(query),
      queryFn: () => collectionsApi.listMine(query),
    }),

  collection: (collectionId: number) =>
    queryOptions({
      queryKey: libraryQueryKeys.collectionDetail(collectionId),
      queryFn: () => collectionsApi.getMine(collectionId),
    }),

  collectionItems: (collectionId: number) =>
    queryOptions({
      queryKey: libraryQueryKeys.collectionItems(collectionId),
      queryFn: () => collectionsApi.listItems(collectionId),
    }),
};

export const libraryMutations = {
  createUserSubject: () =>
    mutationOptions({
      mutationFn: (body: CreateUserSubjectBody) => userSubjectsApi.createMine(body),
    }),

  updateUserSubject: () =>
    mutationOptions({
      mutationFn: ({ userSubjectId, body }: { userSubjectId: number; body: Partial<Omit<UserSubject, 'id' | 'subject'>> }) =>
        userSubjectsApi.updateMine(userSubjectId, body),
    }),

  deleteUserSubject: () =>
    mutationOptions({
      mutationFn: (userSubjectId: number) => userSubjectsApi.deleteMine(userSubjectId),
    }),

  replaceProgress: () =>
    mutationOptions({
      mutationFn: ({ subjectId, finishedEpisodeIds }: { subjectId: UUID; finishedEpisodeIds: number[] }) =>
        progressApi.replaceFinishedEpisodes(subjectId, finishedEpisodeIds),
    }),

  setEpisodeFinished: () =>
    mutationOptions({
      mutationFn: ({ subjectId, episodeId, isFinished }: { subjectId: UUID; episodeId: number; isFinished: boolean }) =>
        progressApi.setEpisodeFinished(subjectId, episodeId, isFinished),
    }),

  replaceTags: () =>
    mutationOptions({
      mutationFn: ({ subjectId, tagNames }: { subjectId: UUID; tagNames: string[] }) =>
        tagsApi.replaceForSubject(subjectId, { tag_names: tagNames }),
    }),

  replaceRatingDetails: () =>
    mutationOptions({
      mutationFn: ({ subjectId, details }: { subjectId: UUID; details: RatingDetail[] }) =>
        ratingDetailsApi.replaceForSubject(subjectId, details),
    }),

  createReview: () =>
    mutationOptions({
      mutationFn: ({ subjectId, body }: { subjectId: UUID; body: Pick<Review, 'title' | 'content'> & Partial<Pick<Review, 'is_public' | 'is_spoiler'>> }) =>
        reviewsApi.createForSubject(subjectId, body),
    }),

  updateReview: () =>
    mutationOptions({
      mutationFn: ({ reviewId, body }: { reviewId: number; body: Partial<Pick<Review, 'title' | 'content' | 'is_public' | 'is_spoiler'>> }) =>
        reviewsApi.updateMine(reviewId, body),
    }),

  deleteReview: () =>
    mutationOptions({
      mutationFn: (reviewId: number) => reviewsApi.deleteMine(reviewId),
    }),
};
