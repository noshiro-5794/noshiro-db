import {
  api,
  decodeApiPage,
  decodeCollection,
  decodeCollectionItem,
  decodeCollectionItems,
  decodeProgressSummary,
  decodePublicReview,
  decodeRatingDetails,
  decodeReview,
  decodeReviews,
  decodeTag,
  decodeTags,
  decodeUserSubject,
  decodeUserSubjectContext,
  encodePath,
} from '@/shared/api';
import type {
  ApiPage,
  ApiRequestContext,
  Collection,
  CollectionItem,
  PageQuery,
  PrimarySubjectType,
  ProgressSummary,
  RatingDetail,
  Review,
  Tag,
  UUID,
  UserSubject,
  UserSubjectContext,
  UserSubjectStatus,
} from '@/shared/api';

export type UserSubjectListQuery = PageQuery & {
  status?: UserSubjectStatus;
  subject_type?: PrimarySubjectType;
  keyword?: string;
  tag_id?: number;
  ordering?: string;
};

export type UserSubjectWriteBody = {
  status?: UserSubjectStatus;
  simple_rating?: number | null;
  rating?: string | null;
  comment?: string;
  watch_start_date?: string | null;
  watch_end_date?: string | null;
  is_public?: boolean;
};

export type CreateUserSubjectBody = UserSubjectWriteBody & {
  subject_id: UUID;
  status: UserSubjectStatus;
};

export type ReviewListQuery = PageQuery & {
  keyword?: string;
  ordering?: 'created_at' | '-created_at' | 'id' | '-id';
};

export type CollectionListQuery = PageQuery & {
  keyword?: string;
  ordering?: 'id' | '-id' | 'name' | '-name' | 'simple_rating' | '-simple_rating' | 'item_count' | '-item_count';
};

export const userSubjectsApi = {
  listMine: (query: UserSubjectListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<UserSubject>>('/api/users/me/subjects/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeUserSubject),
      query,
    }),

  createMine: (body: CreateUserSubjectBody) =>
    api.post<UserSubject, CreateUserSubjectBody>('/api/users/me/subjects/', body, { decode: decodeUserSubject }),

  getMine: (userSubjectId: number, context: ApiRequestContext = {}) =>
    api.get<UserSubject>(`/api/users/me/subjects/${encodePath(userSubjectId)}/`, {
      ...context,
      decode: decodeUserSubject,
    }),

  getContext: (subjectId: UUID, context: ApiRequestContext = {}) =>
    api.get<UserSubjectContext>(`/api/users/me/subjects/${encodePath(subjectId)}/context/`, {
      ...context,
      decode: decodeUserSubjectContext,
    }),

  updateMine: (userSubjectId: number, body: UserSubjectWriteBody) =>
    api.patch<UserSubject, typeof body>(`/api/users/me/subjects/${encodePath(userSubjectId)}/`, body, {
      decode: decodeUserSubject,
    }),

  deleteMine: (userSubjectId: number) => api.delete<unknown>(`/api/users/me/subjects/${encodePath(userSubjectId)}/`),
};

export const progressApi = {
  get: (subjectId: UUID, context: ApiRequestContext = {}) =>
    api.get<ProgressSummary>(`/api/users/me/subjects/${encodePath(subjectId)}/episodes/progress/`, {
      ...context,
      decode: decodeProgressSummary,
    }),

  replaceFinishedEpisodes: (subjectId: UUID, finishedEpisodeIds: number[]) =>
    api.put<ProgressSummary, { finished_episode_ids: number[] }>(
      `/api/users/me/subjects/${encodePath(subjectId)}/episodes/progress/`,
      { finished_episode_ids: finishedEpisodeIds },
      { decode: decodeProgressSummary },
    ),

  setEpisodeFinished: (subjectId: UUID, episodeId: number, isFinished: boolean) =>
    api.patch<ProgressSummary, { is_finished: boolean }>(
      `/api/users/me/subjects/${encodePath(subjectId)}/episodes/${encodePath(episodeId)}/progress/`,
      { is_finished: isFinished },
      { decode: decodeProgressSummary },
    ),
};

export const tagsApi = {
  listMine: (query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Tag>>('/api/users/me/tags/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeTag),
      query,
    }),

  createOrReuse: (body: { name: string }) =>
    api.post<Tag, typeof body>('/api/users/me/tags/', body, { decode: decodeTag }),

  update: (tagId: number, body: { name: string }) =>
    api.patch<Tag, typeof body>(`/api/users/me/tags/${encodePath(tagId)}/`, body, { decode: decodeTag }),

  getForSubject: (subjectId: UUID, context: ApiRequestContext = {}) =>
    api.get<Tag[]>(`/api/users/me/subjects/${encodePath(subjectId)}/tags/`, { ...context, decode: decodeTags }),

  replaceForSubject: (subjectId: UUID, body: { tag_ids?: number[]; tag_names?: string[] }) =>
    api.put<Tag[], typeof body>(`/api/users/me/subjects/${encodePath(subjectId)}/tags/`, body, {
      decode: decodeTags,
    }),

  delete: (tagId: number) => api.delete<unknown>(`/api/users/me/tags/${encodePath(tagId)}/`),
};

export const ratingDetailsApi = {
  getForSubject: (subjectId: UUID, context: ApiRequestContext = {}) =>
    api.get<RatingDetail[]>(`/api/users/me/subjects/${encodePath(subjectId)}/rating-details/`, {
      ...context,
      decode: decodeRatingDetails,
    }),

  replaceForSubject: (subjectId: UUID, details: RatingDetail[]) =>
    api.put<RatingDetail[], { details: RatingDetail[] }>(
      `/api/users/me/subjects/${encodePath(subjectId)}/rating-details/`,
      { details },
      { decode: decodeRatingDetails },
    ),
};

export const reviewsApi = {
  listMine: (query: ReviewListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Review>>('/api/users/me/reviews/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeReview),
      query,
    }),

  listForSubject: (subjectId: UUID, context: ApiRequestContext = {}) =>
    api.get<Review[]>(`/api/users/me/subjects/${encodePath(subjectId)}/reviews/`, {
      ...context,
      decode: decodeReviews,
    }),

  listPublicForSubject: (subjectId: UUID, query: ReviewListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Review>>(`/api/users/subjects/${encodePath(subjectId)}/reviews/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodePublicReview),
      query,
    }),

  createForSubject: (
    subjectId: UUID,
    body: { title: string; content: string; is_public?: boolean; is_spoiler?: boolean },
  ) =>
    api.post<Review, typeof body>(`/api/users/me/subjects/${encodePath(subjectId)}/reviews/`, body, {
      decode: decodeReview,
    }),

  getMine: (reviewId: number, context: ApiRequestContext = {}) =>
    api.get<Review>(`/api/users/me/reviews/${encodePath(reviewId)}/`, { ...context, decode: decodeReview }),

  getPublic: (reviewId: number, context: ApiRequestContext = {}) =>
    api.get<Review>(`/api/users/reviews/${encodePath(reviewId)}/`, { ...context, decode: decodePublicReview }),

  updateMine: (reviewId: number, body: Partial<Pick<Review, 'title' | 'content' | 'is_public' | 'is_spoiler'>>) =>
    api.patch<Review, typeof body>(`/api/users/me/reviews/${encodePath(reviewId)}/`, body, { decode: decodeReview }),

  deleteMine: (reviewId: number) => api.delete<unknown>(`/api/users/me/reviews/${encodePath(reviewId)}/`),
};

export const collectionsApi = {
  listMine: (query: CollectionListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Collection>>('/api/users/me/collections/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCollection),
      query,
    }),

  createMine: (body: { name: string; simple_rating?: number; note?: string; is_public?: boolean }) =>
    api.post<Collection, typeof body>('/api/users/me/collections/', body, { decode: decodeCollection }),

  getMine: (collectionId: number, context: ApiRequestContext = {}) =>
    api.get<Collection>(`/api/users/me/collections/${encodePath(collectionId)}/`, {
      ...context,
      decode: decodeCollection,
    }),

  updateMine: (
    collectionId: number,
    body: Partial<Pick<Collection, 'name' | 'simple_rating' | 'note' | 'is_public'>>,
  ) =>
    api.patch<Collection, typeof body>(`/api/users/me/collections/${encodePath(collectionId)}/`, body, {
      decode: decodeCollection,
    }),

  listItems: (collectionId: number, query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CollectionItem>>(`/api/users/me/collections/${encodePath(collectionId)}/items/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCollectionItem),
      query,
    }),

  addItem: (
    collectionId: number,
    body: { subject_id?: UUID; user_subject_id?: number; order?: number; relation?: string },
  ) =>
    api.post<CollectionItem, typeof body>(`/api/users/me/collections/${encodePath(collectionId)}/items/`, body, {
      decode: decodeCollectionItem,
    }),

  replaceItems: (
    collectionId: number,
    items: Array<{ subject_id?: UUID; user_subject_id?: number; order?: number; relation?: string }>,
  ) =>
    api.put<CollectionItem[], { items: typeof items }>(
      `/api/users/me/collections/${encodePath(collectionId)}/items/`,
      { items },
      { decode: decodeCollectionItems },
    ),

  updateItems: (collectionId: number, items: Array<{ id: number; order?: number; relation?: string }>) =>
    api.patch<CollectionItem[], { items: typeof items }>(
      `/api/users/me/collections/${encodePath(collectionId)}/items/`,
      { items },
      { decode: decodeCollectionItems },
    ),

  deleteItem: (collectionId: number, itemId: number) =>
    api.delete<unknown>(`/api/users/me/collections/${encodePath(collectionId)}/items/${encodePath(itemId)}/`),

  deleteMine: (collectionId: number) => api.delete<unknown>(`/api/users/me/collections/${encodePath(collectionId)}/`),
};
