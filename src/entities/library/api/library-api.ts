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
  entity_id: UUID;
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

async function findLibraryEntry(entityId: UUID, context: ApiRequestContext = {}) {
  for (let page = 1; page <= 50; page += 1) {
    const response = await userSubjectsApi.listMine({ page, page_size: 100 }, context);
    const entry = response.results.find((item) => item.subject.id === entityId);
    if (entry) return entry;
    if (!response.next || response.results.length === 0) return null;
  }

  return null;
}

export const userSubjectsApi = {
  listMine: (query: UserSubjectListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<UserSubject>>('/api/v1/users/me/library/entries/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeUserSubject),
      query: {
        ...(query.page === undefined ? {} : { page: query.page }),
        ...(query.page_size === undefined ? {} : { page_size: query.page_size }),
        ...(query.status === undefined ? {} : { status: query.status }),
      },
    }),

  createMine: (body: CreateUserSubjectBody) =>
    api.post<UserSubject, CreateUserSubjectBody>('/api/v1/users/me/library/entries/', body, {
      decode: decodeUserSubject,
    }),

  getMine: (userSubjectId: number, context: ApiRequestContext = {}) =>
    api.get<UserSubject>(`/api/v1/users/me/library/entries/${encodePath(userSubjectId)}/`, {
      ...context,
      decode: decodeUserSubject,
    }),

  getContext: async (subjectId: UUID, context: ApiRequestContext = {}): Promise<UserSubjectContext> => {
    const page = await userSubjectsApi.listMine({ page_size: 100 }, context);
    const entry = page.results.find((item) => item.subject.id === subjectId) ?? null;
    if (!entry) {
      return {
        is_marked: false,
        user_subject: null,
        tags: [],
        rating_details: [],
        reviews: [],
        progress: {
          subject_id: subjectId,
          user_subject_id: null,
          total_episodes: 0,
          finished_count: 0,
          finished_episode_ids: [],
          episodes: [],
        },
      };
    }

    const [tags, ratingDetails, reviews, progress] = await Promise.all([
      tagsApi.getForEntry(entry.id, context),
      ratingDetailsApi.getForEntry(entry.id, context),
      reviewsApi.listForEntry(entry.id, context),
      progressApi.getForEntry(entry.id, context),
    ]);

    return {
      is_marked: true,
      user_subject: entry,
      tags,
      rating_details: ratingDetails,
      reviews,
      progress,
    };
  },

  updateMine: (userSubjectId: number, body: UserSubjectWriteBody) =>
    api.patch<UserSubject, typeof body>(`/api/v1/users/me/library/entries/${encodePath(userSubjectId)}/`, body, {
      decode: decodeUserSubject,
    }),

  deleteMine: (userSubjectId: number) =>
    api.delete<unknown>(`/api/v1/users/me/library/entries/${encodePath(userSubjectId)}/`),
};

export const progressApi = {
  getForEntry: (entryId: number, context: ApiRequestContext = {}) =>
    api.get<ProgressSummary>(`/api/v1/users/me/library/entries/${encodePath(entryId)}/episodes/progress/`, {
      ...context,
      decode: decodeProgressSummary,
    }),

  get: async (subjectId: UUID, context: ApiRequestContext = {}) => {
    const entry = await findLibraryEntry(subjectId, context);
    if (!entry) {
      return {
        subject_id: subjectId,
        user_subject_id: null,
        total_episodes: 0,
        finished_count: 0,
        finished_episode_ids: [],
        episodes: [],
      } satisfies ProgressSummary;
    }
    return progressApi.getForEntry(entry.id, context);
  },

  replaceFinishedEpisodes: (subjectId: UUID, finishedEpisodeIds: string[]) =>
    findLibraryEntry(subjectId).then(async (entry) => {
      if (!entry) throw new TypeError('Library entry not found');
      return progressApi.replaceFinishedEpisodesForEntry(entry.id, finishedEpisodeIds);
    }),

  replaceFinishedEpisodesForEntry: (entryId: number, finishedEpisodeIds: string[]) =>
    api.put<ProgressSummary, { finished_episode_ids: string[] }>(
      `/api/v1/users/me/library/entries/${encodePath(entryId)}/episodes/progress/`,
      { finished_episode_ids: finishedEpisodeIds },
      { decode: decodeProgressSummary },
    ),

  setEpisodeFinished: async (subjectId: UUID, episodeId: number | string, isFinished: boolean) => {
    const entry = await findLibraryEntry(subjectId);
    if (!entry) throw new TypeError('Library entry not found');
    return isFinished
      ? api.put<ProgressSummary>(
          `/api/v1/users/me/library/entries/${encodePath(entry.id)}/episodes/${encodePath(episodeId)}/progress/`,
          undefined,
          {
            decode: decodeProgressSummary,
          },
        )
      : api.delete<ProgressSummary>(
          `/api/v1/users/me/library/entries/${encodePath(entry.id)}/episodes/${encodePath(episodeId)}/progress/`,
          {
            decode: decodeProgressSummary,
          },
        );
  },
};

export const tagsApi = {
  listMine: (query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Tag>>('/api/v1/users/me/tags/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeTag),
      query,
    }),

  createOrReuse: (body: { name: string }) =>
    api.post<Tag, typeof body>('/api/v1/users/me/tags/', body, { decode: decodeTag }),

  update: (tagId: number, body: { name: string }) =>
    api.patch<Tag, typeof body>(`/api/v1/users/me/tags/${encodePath(tagId)}/`, body, { decode: decodeTag }),

  getForEntry: (entryId: number, context: ApiRequestContext = {}) =>
    api.get<Tag[]>(`/api/v1/users/me/library/entries/${encodePath(entryId)}/tags/`, { ...context, decode: decodeTags }),

  getForSubject: async (subjectId: UUID, context: ApiRequestContext = {}) => {
    const entry = await findLibraryEntry(subjectId, context);
    if (!entry) return [];
    return tagsApi.getForEntry(entry.id, context);
  },

  replaceForSubject: (subjectId: UUID, body: { tag_ids?: number[]; tag_names?: string[] }) =>
    findLibraryEntry(subjectId).then((entry) => {
      if (!entry) throw new TypeError('Library entry not found');
      return api.put<Tag[], typeof body>(`/api/v1/users/me/library/entries/${encodePath(entry.id)}/tags/`, body, {
        decode: decodeTags,
      });
    }),

  delete: (tagId: number) => api.delete<unknown>(`/api/v1/users/me/tags/${encodePath(tagId)}/`),
};

export const ratingDetailsApi = {
  getForEntry: (entryId: number, context: ApiRequestContext = {}) =>
    api.get<RatingDetail[]>(`/api/v1/users/me/library/entries/${encodePath(entryId)}/rating-details/`, {
      ...context,
      decode: decodeRatingDetails,
    }),

  getForSubject: async (subjectId: UUID, context: ApiRequestContext = {}) => {
    const entry = await findLibraryEntry(subjectId, context);
    if (!entry) return [];
    return ratingDetailsApi.getForEntry(entry.id, context);
  },

  replaceForSubject: (subjectId: UUID, details: RatingDetail[]) =>
    findLibraryEntry(subjectId).then((entry) => {
      if (!entry) throw new TypeError('Library entry not found');
      return api.put<RatingDetail[], { details: RatingDetail[] }>(
        `/api/v1/users/me/library/entries/${encodePath(entry.id)}/rating-details/`,
        { details },
        { decode: decodeRatingDetails },
      );
    }),
};

export const reviewsApi = {
  listMine: (query: ReviewListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Review>>('/api/v1/users/me/reviews/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeReview),
      query,
    }),

  listForEntry: (entryId: number, context: ApiRequestContext = {}) =>
    api.get<Review[]>(`/api/v1/users/me/library/entries/${encodePath(entryId)}/reviews/`, {
      ...context,
      decode: decodeReviews,
    }),

  listForSubject: async (subjectId: UUID, context: ApiRequestContext = {}) => {
    const entry = await findLibraryEntry(subjectId, context);
    if (!entry) return [];
    return reviewsApi.listForEntry(entry.id, context);
  },

  listPublicForSubject: (subjectId: UUID, query: ReviewListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Review>>(`/api/v1/users/entities/${encodePath(subjectId)}/reviews/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodePublicReview),
      query: {
        ...(query.page === undefined ? {} : { page: query.page }),
        ...(query.page_size === undefined ? {} : { page_size: query.page_size }),
      },
    }),

  createForSubject: (
    subjectId: UUID,
    body: { title: string; content: string; is_public?: boolean; is_spoiler?: boolean },
  ) =>
    findLibraryEntry(subjectId).then((entry) => {
      if (!entry) throw new TypeError('Library entry not found');
      return api.post<Review, typeof body>(`/api/v1/users/me/library/entries/${encodePath(entry.id)}/reviews/`, body, {
        decode: decodeReview,
      });
    }),

  getMine: (reviewId: number, context: ApiRequestContext = {}) =>
    api.get<Review>(`/api/v1/users/me/reviews/${encodePath(reviewId)}/`, { ...context, decode: decodeReview }),

  getPublic: (reviewId: number, context: ApiRequestContext = {}) =>
    api.get<Review>(`/api/v1/users/reviews/${encodePath(reviewId)}/`, { ...context, decode: decodePublicReview }),

  updateMine: (reviewId: number, body: Partial<Pick<Review, 'title' | 'content' | 'is_public' | 'is_spoiler'>>) =>
    api.patch<Review, typeof body>(`/api/v1/users/me/reviews/${encodePath(reviewId)}/`, body, { decode: decodeReview }),

  deleteMine: (reviewId: number) => api.delete<unknown>(`/api/v1/users/me/reviews/${encodePath(reviewId)}/`),
};

export const collectionsApi = {
  listMine: (query: CollectionListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<Collection>>('/api/v1/users/me/collections/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCollection),
      query,
    }),

  createMine: (body: { name: string; simple_rating?: number; note?: string; is_public?: boolean }) =>
    api.post<Collection, typeof body>('/api/v1/users/me/collections/', body, { decode: decodeCollection }),

  getMine: (collectionId: number, context: ApiRequestContext = {}) =>
    api.get<Collection>(`/api/v1/users/me/collections/${encodePath(collectionId)}/`, {
      ...context,
      decode: decodeCollection,
    }),

  updateMine: (
    collectionId: number,
    body: Partial<Pick<Collection, 'name' | 'simple_rating' | 'note' | 'is_public'>>,
  ) =>
    api.patch<Collection, typeof body>(`/api/v1/users/me/collections/${encodePath(collectionId)}/`, body, {
      decode: decodeCollection,
    }),

  listItems: (collectionId: number, query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<CollectionItem>>(`/api/v1/users/me/collections/${encodePath(collectionId)}/items/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeCollectionItem),
      query,
    }),

  addItem: (collectionId: number, body: { library_entry_id?: number; order?: number; relation?: string }) =>
    api.post<CollectionItem, typeof body>(`/api/v1/users/me/collections/${encodePath(collectionId)}/items/`, body, {
      decode: decodeCollectionItem,
    }),

  replaceItems: (
    collectionId: number,
    items: Array<{ library_entry_id?: number; order?: number; relation?: string }>,
  ) =>
    api.put<CollectionItem[], { items: typeof items }>(
      `/api/v1/users/me/collections/${encodePath(collectionId)}/items/`,
      { items },
      { decode: decodeCollectionItems },
    ),

  updateItems: (collectionId: number, items: Array<{ id: number; order?: number; relation?: string }>) =>
    api.patch<CollectionItem[], { items: typeof items }>(
      `/api/v1/users/me/collections/${encodePath(collectionId)}/items/`,
      { items },
      { decode: decodeCollectionItems },
    ),

  deleteItem: (collectionId: number, itemId: number) =>
    api.delete<unknown>(`/api/v1/users/me/collections/${encodePath(collectionId)}/items/${encodePath(itemId)}/`),

  deleteMine: (collectionId: number) =>
    api.delete<unknown>(`/api/v1/users/me/collections/${encodePath(collectionId)}/`),
};
