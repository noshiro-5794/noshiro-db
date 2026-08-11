import { infiniteQueryOptions, mutationOptions, queryOptions } from '@tanstack/react-query';
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
  type UserSubjectWriteBody,
} from '../api/library-api';
import { getNextApiPageParam, type PageQuery, type RatingDetail, type Review, type UUID } from '@/shared/api';

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
  reviewLists: () => [...libraryQueryKeys.reviews(), 'list'] as const,
  reviewList: (query: ReviewListQuery = {}) => [...libraryQueryKeys.reviewLists(), query] as const,
  subjectReviews: (subjectId: UUID) => [...libraryQueryKeys.reviews(), 'subject', subjectId] as const,
  publicSubjectReviews: (subjectId: UUID, query: ReviewListQuery = {}) =>
    [...libraryQueryKeys.reviews(), 'subject-public', subjectId, query] as const,
  reviewDetail: (reviewId: number) => [...libraryQueryKeys.reviews(), 'detail', reviewId] as const,
  publicReviewDetail: (reviewId: number) => [...libraryQueryKeys.reviews(), 'public-detail', reviewId] as const,
  collections: () => [...libraryQueryKeys.all, 'collections'] as const,
  collectionList: (query: CollectionListQuery = {}) => [...libraryQueryKeys.collections(), 'list', query] as const,
  collectionDetail: (collectionId: number) => [...libraryQueryKeys.collections(), 'detail', collectionId] as const,
  collectionItems: (collectionId: number) => [...libraryQueryKeys.collections(), 'items', collectionId] as const,
  collectionItemList: (collectionId: number, query: PageQuery = {}) =>
    [...libraryQueryKeys.collectionItems(collectionId), 'list', query] as const,
  collectionItemInfinite: (collectionId: number, pageSize: number) =>
    [...libraryQueryKeys.collectionItems(collectionId), 'infinite', pageSize] as const,
};

export const libraryQueries = {
  userSubjects: (query: UserSubjectListQuery = {}) =>
    queryOptions({
      queryKey: libraryQueryKeys.userSubjectList(query),
      queryFn: ({ signal }) => userSubjectsApi.listMine(query, { signal }),
    }),

  userSubject: (userSubjectId: number) =>
    queryOptions({
      queryKey: libraryQueryKeys.userSubjectDetail(userSubjectId),
      queryFn: ({ signal }) => userSubjectsApi.getMine(userSubjectId, { signal }),
    }),

  subjectContext: (subjectId: UUID) =>
    queryOptions({
      queryKey: libraryQueryKeys.subjectContext(subjectId),
      queryFn: ({ signal }) => userSubjectsApi.getContext(subjectId, { signal }),
    }),

  progress: (subjectId: UUID) =>
    queryOptions({
      queryKey: libraryQueryKeys.progress(subjectId),
      queryFn: ({ signal }) => progressApi.get(subjectId, { signal }),
    }),

  tags: () =>
    queryOptions({
      queryKey: libraryQueryKeys.tagList(),
      queryFn: ({ signal }) => tagsApi.listMine({}, { signal }),
    }),

  subjectTags: (subjectId: UUID) =>
    queryOptions({
      queryKey: libraryQueryKeys.subjectTags(subjectId),
      queryFn: ({ signal }) => tagsApi.getForSubject(subjectId, { signal }),
    }),

  ratingDetails: (subjectId: UUID) =>
    queryOptions({
      queryKey: libraryQueryKeys.ratingDetails(subjectId),
      queryFn: ({ signal }) => ratingDetailsApi.getForSubject(subjectId, { signal }),
    }),

  reviews: (query: ReviewListQuery = {}) =>
    queryOptions({
      queryKey: libraryQueryKeys.reviewList(query),
      queryFn: ({ signal }) => reviewsApi.listMine(query, { signal }),
    }),

  subjectReviews: (subjectId: UUID) =>
    queryOptions({
      queryKey: libraryQueryKeys.subjectReviews(subjectId),
      queryFn: ({ signal }) => reviewsApi.listForSubject(subjectId, { signal }),
    }),

  publicSubjectReviews: (subjectId: UUID, query: ReviewListQuery = {}) =>
    queryOptions({
      queryKey: libraryQueryKeys.publicSubjectReviews(subjectId, query),
      queryFn: ({ signal }) => reviewsApi.listPublicForSubject(subjectId, query, { signal }),
    }),

  review: (reviewId: number) =>
    queryOptions({
      queryKey: libraryQueryKeys.reviewDetail(reviewId),
      queryFn: ({ signal }) => reviewsApi.getMine(reviewId, { signal }),
    }),

  publicReview: (reviewId: number) =>
    queryOptions({
      queryKey: libraryQueryKeys.publicReviewDetail(reviewId),
      queryFn: ({ signal }) => reviewsApi.getPublic(reviewId, { signal }),
    }),

  collections: (query: CollectionListQuery = {}) =>
    queryOptions({
      queryKey: libraryQueryKeys.collectionList(query),
      queryFn: ({ signal }) => collectionsApi.listMine(query, { signal }),
    }),

  collection: (collectionId: number) =>
    queryOptions({
      queryKey: libraryQueryKeys.collectionDetail(collectionId),
      queryFn: ({ signal }) => collectionsApi.getMine(collectionId, { signal }),
    }),

  collectionItems: (collectionId: number, query: PageQuery = {}) =>
    queryOptions({
      queryKey: libraryQueryKeys.collectionItemList(collectionId, query),
      queryFn: ({ signal }) => collectionsApi.listItems(collectionId, query, { signal }),
    }),

  collectionItemsInfinite: (collectionId: number, pageSize = 64) =>
    infiniteQueryOptions({
      queryKey: libraryQueryKeys.collectionItemInfinite(collectionId, pageSize),
      initialPageParam: 1,
      queryFn: ({ pageParam, signal }) =>
        collectionsApi.listItems(collectionId, { page: pageParam, page_size: pageSize }, { signal }),
      getNextPageParam: getNextApiPageParam,
    }),
};

export const libraryMutations = {
  createUserSubject: () =>
    mutationOptions({
      mutationFn: (body: CreateUserSubjectBody) => userSubjectsApi.createMine(body),
    }),

  updateUserSubject: () =>
    mutationOptions({
      mutationFn: ({ userSubjectId, body }: { userSubjectId: number; body: UserSubjectWriteBody }) =>
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

  deleteTag: () =>
    mutationOptions({
      mutationFn: (tagId: number) => tagsApi.delete(tagId),
    }),

  replaceRatingDetails: () =>
    mutationOptions({
      mutationFn: ({ subjectId, details }: { subjectId: UUID; details: RatingDetail[] }) =>
        ratingDetailsApi.replaceForSubject(subjectId, details),
    }),

  createReview: () =>
    mutationOptions({
      mutationFn: ({
        subjectId,
        body,
      }: {
        subjectId: UUID;
        body: Pick<Review, 'title' | 'content'> & Partial<Pick<Review, 'is_public' | 'is_spoiler'>>;
      }) => reviewsApi.createForSubject(subjectId, body),
    }),

  updateReview: () =>
    mutationOptions({
      mutationFn: ({
        reviewId,
        body,
      }: {
        reviewId: number;
        body: Partial<Pick<Review, 'title' | 'content' | 'is_public' | 'is_spoiler'>>;
      }) => reviewsApi.updateMine(reviewId, body),
    }),

  deleteReview: () =>
    mutationOptions({
      mutationFn: (reviewId: number) => reviewsApi.deleteMine(reviewId),
    }),

  createCollection: () =>
    mutationOptions({
      mutationFn: (body: { name: string; simple_rating?: number; note?: string; is_public?: boolean }) =>
        collectionsApi.createMine(body),
    }),

  updateCollection: () =>
    mutationOptions({
      mutationFn: ({
        collectionId,
        body,
      }: {
        collectionId: number;
        body: Partial<{ name: string; simple_rating: number; note: string; is_public: boolean }>;
      }) => collectionsApi.updateMine(collectionId, body),
    }),

  deleteCollection: () =>
    mutationOptions({
      mutationFn: (collectionId: number) => collectionsApi.deleteMine(collectionId),
    }),

  deleteCollectionItem: () =>
    mutationOptions({
      mutationFn: ({ collectionId, itemId }: { collectionId: number; itemId: number }) =>
        collectionsApi.deleteItem(collectionId, itemId),
    }),

  addCollectionItem: () =>
    mutationOptions({
      mutationFn: ({
        collectionId,
        body,
      }: {
        collectionId: number;
        body: { subject_id?: UUID; user_subject_id?: number; order?: number; relation?: string };
      }) => collectionsApi.addItem(collectionId, body),
    }),

  updateCollectionItems: () =>
    mutationOptions({
      mutationFn: ({
        collectionId,
        items,
      }: {
        collectionId: number;
        items: Array<{ id: number; order?: number; relation?: string }>;
      }) => collectionsApi.updateItems(collectionId, items),
    }),
};
