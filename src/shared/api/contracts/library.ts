import type { DateString, DecimalString, ISODateString, UUID } from './common';
import type { SubjectEpisode, SubjectSummary } from './subject';
import type { PublicUserSummary } from './user';

export type UserSubjectStatus = 'wish' | 'doing' | 'done' | 'on_hold' | 'drop' | (string & {});

export type UserSubject = {
  id: number;
  status: UserSubjectStatus;
  simple_rating: number | null;
  rating: DecimalString | null;
  comment: string;
  watch_start_date: DateString;
  watch_end_date: DateString;
  is_public: boolean;
  created_at?: ISODateString;
  updated_at?: ISODateString;
  subject: Pick<SubjectSummary, 'id' | 'title'> & Partial<SubjectSummary>;
} & Record<string, unknown>;

export type Tag = {
  id: number;
  name: string;
};

export type RatingDetail = {
  key: string;
  value: DecimalString;
};

export type Review = {
  id: number;
  title: string;
  content: string;
  is_public: boolean;
  is_spoiler: boolean;
  reaction_count?: number;
  created_at?: ISODateString;
  updated_at?: ISODateString;
  subject?: SubjectSummary;
  user?: PublicUserSummary;
  viewer_state?: {
    has_liked: boolean;
    has_bookmarked: boolean;
  };
} & Record<string, unknown>;

export type ProgressSummary = {
  subject_id?: UUID;
  user_subject_id?: number | null;
  total_episodes?: number;
  finished_count: number;
  finished_episode_ids: number[];
  episodes?: Array<SubjectEpisode & { is_finished: boolean }>;
};

export type UserSubjectContext = {
  is_marked: boolean;
  user_subject: UserSubject | null;
  tags: Tag[];
  rating_details: RatingDetail[];
  reviews: Review[];
  progress: ProgressSummary;
};

export type Collection = {
  id: number;
  name: string;
  simple_rating: number | null;
  note: string;
  is_public: boolean;
  item_count?: number;
  reaction_count?: number;
  created_at?: ISODateString;
  updated_at?: ISODateString;
  viewer_state?: {
    has_liked: boolean;
    has_bookmarked: boolean;
  };
} & Record<string, unknown>;

export type CollectionItem = {
  id: number;
  user_subject: Pick<
    UserSubject,
    'id' | 'status' | 'simple_rating' | 'rating' | 'comment' | 'watch_start_date' | 'watch_end_date' | 'is_public'
  >;
  subject: SubjectSummary;
  order: number;
  relation: string;
} & Record<string, unknown>;
