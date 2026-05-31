import { api } from '@/lib/api/client';
import { encodePath } from '@/lib/api/path';
import type {
  ApiPage,
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
} from '@/lib/api/types';

export type UserSubjectListQuery = PageQuery & {
  status?: UserSubjectStatus;
  subject_type?: PrimarySubjectType;
  keyword?: string;
  tag_id?: number;
  ordering?: string;
};

export type CreateUserSubjectBody = {
  subject_id: UUID;
  status: UserSubjectStatus;
  simple_rating?: number;
  rating?: string;
  comment?: string;
  watch_start_date?: string;
  watch_end_date?: string;
  is_public?: boolean;
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
  listMine: (query: UserSubjectListQuery = {}) => api.get<ApiPage<UserSubject>>('/api/users/me/subjects/', { query }),

  createMine: (body: CreateUserSubjectBody) =>
    api.post<UserSubject, CreateUserSubjectBody>('/api/users/me/subjects/', body),

  getMine: (userSubjectId: number) => api.get<UserSubject>(`/api/users/me/subjects/${encodePath(userSubjectId)}/`),

  getContext: (subjectId: UUID) => api.get<UserSubjectContext>(`/api/users/me/subjects/${encodePath(subjectId)}/context/`),

  updateMine: (userSubjectId: number, body: Partial<Omit<UserSubject, 'id' | 'subject'>>) =>
    api.patch<UserSubject, typeof body>(`/api/users/me/subjects/${encodePath(userSubjectId)}/`, body),

  deleteMine: (userSubjectId: number) => api.delete<unknown>(`/api/users/me/subjects/${encodePath(userSubjectId)}/`),
};

export const progressApi = {
  get: (subjectId: UUID) => api.get<ProgressSummary>(`/api/users/me/subjects/${encodePath(subjectId)}/episodes/progress/`),

  replaceFinishedEpisodes: (subjectId: UUID, finishedEpisodeIds: number[]) =>
    api.put<ProgressSummary, { finished_episode_ids: number[] }>(
      `/api/users/me/subjects/${encodePath(subjectId)}/episodes/progress/`,
      { finished_episode_ids: finishedEpisodeIds },
    ),

  setEpisodeFinished: (subjectId: UUID, episodeId: number, isFinished: boolean) =>
    api.patch<ProgressSummary, { is_finished: boolean }>(
      `/api/users/me/subjects/${encodePath(subjectId)}/episodes/${encodePath(episodeId)}/progress/`,
      { is_finished: isFinished },
    ),
};

export const tagsApi = {
  listMine: (query: PageQuery = {}) => api.get<ApiPage<Tag>>('/api/users/me/tags/', { query }),

  createOrReuse: (body: { name: string }) => api.post<Tag, typeof body>('/api/users/me/tags/', body),

  update: (tagId: number, body: { name: string }) =>
    api.patch<Tag, typeof body>(`/api/users/me/tags/${encodePath(tagId)}/`, body),

  getForSubject: (subjectId: UUID) => api.get<Tag[]>(`/api/users/me/subjects/${encodePath(subjectId)}/tags/`),

  replaceForSubject: (subjectId: UUID, body: { tag_ids?: number[]; tag_names?: string[] }) =>
    api.put<Tag[], typeof body>(`/api/users/me/subjects/${encodePath(subjectId)}/tags/`, body),

  delete: (tagId: number) => api.delete<unknown>(`/api/users/me/tags/${encodePath(tagId)}/`),
};

export const ratingDetailsApi = {
  getForSubject: (subjectId: UUID) => api.get<RatingDetail[]>(`/api/users/me/subjects/${encodePath(subjectId)}/rating-details/`),

  replaceForSubject: (subjectId: UUID, details: RatingDetail[]) =>
    api.put<RatingDetail[], { details: RatingDetail[] }>(
      `/api/users/me/subjects/${encodePath(subjectId)}/rating-details/`,
      { details },
    ),
};

export const reviewsApi = {
  listMine: (query: ReviewListQuery = {}) => api.get<ApiPage<Review>>('/api/users/me/reviews/', { query }),

  listForSubject: (subjectId: UUID) => api.get<Review[]>(`/api/users/me/subjects/${encodePath(subjectId)}/reviews/`),

  createForSubject: (subjectId: UUID, body: { title: string; content: string; is_public?: boolean; is_spoiler?: boolean }) =>
    api.post<Review, typeof body>(`/api/users/me/subjects/${encodePath(subjectId)}/reviews/`, body),

  getMine: (reviewId: number) => api.get<Review>(`/api/users/me/reviews/${encodePath(reviewId)}/`),

  updateMine: (reviewId: number, body: Partial<Pick<Review, 'title' | 'content' | 'is_public' | 'is_spoiler'>>) =>
    api.patch<Review, typeof body>(`/api/users/me/reviews/${encodePath(reviewId)}/`, body),

  deleteMine: (reviewId: number) => api.delete<unknown>(`/api/users/me/reviews/${encodePath(reviewId)}/`),
};

export const collectionsApi = {
  listMine: (query: CollectionListQuery = {}) => api.get<ApiPage<Collection>>('/api/users/me/collections/', { query }),

  createMine: (body: { name: string; simple_rating?: number; note?: string; is_public?: boolean }) =>
    api.post<Collection, typeof body>('/api/users/me/collections/', body),

  getMine: (collectionId: number) => api.get<Collection>(`/api/users/me/collections/${encodePath(collectionId)}/`),

  updateMine: (collectionId: number, body: Partial<Pick<Collection, 'name' | 'simple_rating' | 'note' | 'is_public'>>) =>
    api.patch<Collection, typeof body>(`/api/users/me/collections/${encodePath(collectionId)}/`, body),

  listItems: (collectionId: number, query: PageQuery = {}) =>
    api.get<ApiPage<CollectionItem>>(`/api/users/me/collections/${encodePath(collectionId)}/items/`, { query }),

  addItem: (collectionId: number, body: { subject_id?: UUID; user_subject_id?: number; order?: number; relation?: string }) =>
    api.post<CollectionItem, typeof body>(`/api/users/me/collections/${encodePath(collectionId)}/items/`, body),

  replaceItems: (
    collectionId: number,
    items: Array<{ subject_id?: UUID; user_subject_id?: number; order?: number; relation?: string }>,
  ) => api.put<CollectionItem[], { items: typeof items }>(`/api/users/me/collections/${encodePath(collectionId)}/items/`, { items }),

  deleteItem: (collectionId: number, itemId: number) =>
    api.delete<unknown>(`/api/users/me/collections/${encodePath(collectionId)}/items/${encodePath(itemId)}/`),

  deleteMine: (collectionId: number) => api.delete<unknown>(`/api/users/me/collections/${encodePath(collectionId)}/`),
};
