import type { DateString, DecimalString, ISODateString, UUID } from './common';
import type { EntitySummary } from './entity';
import type { SubjectEpisode, SubjectSummary } from './subject';
import type { PublicUserSummary } from './user';

export type LibraryStatus = 'wish' | 'doing' | 'done' | 'on_hold' | 'drop' | (string & {});
export type UserSubjectStatus = LibraryStatus;

export type ReleaseState = {
  release_id: string;
  status: string;
  language: string;
  platform: string;
  note: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: ISODateString;
  updated_at: ISODateString;
};

export type LibraryEntry = {
  id: number;
  entity: EntitySummary;
  status: LibraryStatus;
  simple_rating: number | null;
  rating: DecimalString | null;
  comment: string;
  watch_start_date: DateString | null;
  watch_end_date: DateString | null;
  is_public: boolean;
  releases: ReleaseState[];
  created_at: ISODateString;
  updated_at: ISODateString;
};

export type UserSubject = LibraryEntry & {
  subject: SubjectSummary;
};

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
  reaction_count: number;
  created_at: ISODateString;
  updated_at: ISODateString;
  entity: EntitySummary;
  library_entry_id: number;
  user: PublicUserSummary;
  viewer_state: {
    has_liked: boolean;
    has_bookmarked: boolean;
  };
  subject?: SubjectSummary;
};

export type ProgressSummary = {
  subject_id?: UUID;
  user_subject_id?: number | null;
  entity_id?: UUID;
  library_entry_id?: number;
  total_episodes?: number;
  finished_count: number;
  finished_episode_ids: string[];
  episodes?: Array<SubjectEpisode & { is_finished: boolean }>;
};

export type EpisodeProgressItem = {
  id: string;
  title: string;
  title_cn: string;
  type: string;
  number: string;
  sort: string;
  air_date: string;
  is_finished: boolean;
};

export type EpisodeProgress = {
  library_entry_id: number;
  entity_id: UUID;
  total_episodes: number;
  finished_count: number;
  finished_episode_ids: string[];
  episodes: EpisodeProgressItem[];
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
};

export type CollectionItem = {
  id: number;
  library_entry_id: number;
  entity: EntitySummary;
  order: number;
  relation: string;
  user_subject: UserSubject;
  subject: SubjectSummary;
};

export type LibraryEntryWrite = {
  entity_id?: UUID;
  status?: LibraryStatus;
  simple_rating?: number | null;
  rating?: DecimalString | null;
  comment?: string;
  watch_start_date?: DateString | null;
  watch_end_date?: DateString | null;
  is_public?: boolean;
};

export type ReleaseStatus = 'wish' | 'doing' | 'done' | 'on_hold' | 'drop' | (string & {});

export type ReleaseStateWrite = {
  status: ReleaseStatus;
  language?: string;
  platform?: string;
  note?: string;
  started_at?: string | null;
  completed_at?: string | null;
};

export type UserTagResponse = Tag;
export type UserTagCreateRequest = { name: string };
export type UserTagUpdateRequest = { name: string };
export type UserTagReplaceRequest = { tag_ids?: number[]; tag_names?: string[] };
export type UserSubjectTagReplaceRequest = UserTagReplaceRequest;
export type UserSubjectRatingDetailReplaceRequest = { details: RatingDetail[] };

export type CollectionCreateRequest = {
  name: string;
  simple_rating?: number;
  note?: string;
  is_public?: boolean;
};

export type CollectionUpdateRequest = {
  name?: string;
  simple_rating?: number;
  note?: string;
  is_public?: boolean;
};

export type CollectionItemWrite = {
  library_entry_id?: number;
  order?: number;
  relation?: string;
};

export type CollectionItemPatch = {
  order?: number;
  relation?: string;
};

export type CollectionItemReplace = { items: CollectionItemWrite[] };
export type CollectionItemUpdate = { items: Array<{ id: number; order?: number; relation?: string }> };

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
