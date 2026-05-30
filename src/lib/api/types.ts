export type UUID = string;
export type ISODateString = string;
export type DateString = string;
export type DecimalString = string;

export type ApiPage<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type PageQuery = {
  page?: number;
  page_size?: number;
};

export type PrimarySubjectType = 'anime' | 'galgame';
export type SubjectType = PrimarySubjectType | (string & {});
export type UserSubjectStatus = 'wish' | 'doing' | 'done' | 'on_hold' | 'drop' | (string & {});
export type WeekdayEn = 'Mon' | 'Tue' | 'Wed' | 'Thu' | 'Fri' | 'Sat' | 'Sun';
export type SendCodePurpose = 'register' | 'login' | 'reset_password';
export type ActivityType =
  | 'user_subject_created'
  | 'user_subject_updated'
  | 'review_created'
  | 'collection_created'
  | 'collection_item_added'
  | 'user_followed'
  | (string & {});

export type AccessTokenPayload = {
  access: string;
};

export type CurrentUserProfile = {
  user_id: string;
  email: string;
  is_staff: boolean;
  is_superuser: boolean;
  nickname: string;
  avatar: string | null;
  bio?: string;
  theme_color: string | null;
};

export type PublicUserSummary = {
  id: number;
  nickname: string;
  avatar: string | null;
};

export type PublicUserProfile = PublicUserSummary & {
  bio: string;
  stats: {
    subject_count: number;
    review_count: number;
    collection_count: number;
    following_count: number;
    follower_count: number;
  };
  is_following: boolean;
};

export type SubjectSummary = {
  id: UUID;
  title: string;
  title_cn: string | null;
  subject_type: SubjectType;
  date: DateString | null;
  platform: string | null;
  nsfw: boolean;
  image: string | null;
  image_thumbnail: string | null;
  updated_at?: ISODateString;
  created_at?: ISODateString;
} & Record<string, unknown>;

export type SubjectDetail = SubjectSummary & {
  summary?: string;
  episode_count: number;
  staff_count: number;
  character_count: number;
  infobox?: unknown;
  tags?: string[];
};

export type SubjectEpisode = {
  id: number;
  title: string;
  type: string;
  ep_num: number | null;
  sort: number | null;
  date: DateString | null;
} & Record<string, unknown>;

export type SubjectStaff = {
  id: number;
  name: string;
  name_cn?: string | null;
  role?: string | null;
} & Record<string, unknown>;

export type SubjectCharacter = {
  id: number;
  name: string;
  name_cn?: string | null;
  role?: string | null;
  actors?: SubjectStaff[];
} & Record<string, unknown>;

export type SubjectRelation = {
  relation: string;
  subject: SubjectSummary;
} & Record<string, unknown>;

export type CalendarEntry = {
  weekday_en: WeekdayEn;
  weekday_cn?: string;
  subject: SubjectSummary;
} & Record<string, unknown>;

export type UserSubject = {
  id: number;
  status: UserSubjectStatus;
  simple_rating: number | null;
  rating: DecimalString | null;
  comment: string;
  watch_start_date: DateString | '';
  watch_end_date: DateString | '';
  is_public: boolean;
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
  created_at?: ISODateString;
  updated_at?: ISODateString;
  subject?: SubjectSummary;
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
  created_at?: ISODateString;
  updated_at?: ISODateString;
} & Record<string, unknown>;

export type CollectionItem = {
  id: number;
  subject: SubjectSummary;
  order: number;
  relation: string;
} & Record<string, unknown>;

export type FollowRelation = {
  user: PublicUserSummary;
  followed_at: ISODateString;
};

export type Activity = {
  id: number;
  activity_type: ActivityType;
  created_at: ISODateString;
  user?: PublicUserSummary;
  subject?: SubjectSummary;
  review?: Review;
  collection?: Collection;
  target_user?: PublicUserSummary;
} & Record<string, unknown>;

export type SyncTaskStatus = {
  task_name: string;
  shard: string;
  current_id: number;
  end_id: number;
  status: string;
  fail_count: number;
  updated_at: ISODateString;
};

export type QueuedTask = {
  task_id: string;
  status: 'queued' | string;
};

export type IncrementalSyncResult = {
  task_name: string;
  shard: string;
  start_id: number;
  end_id: number;
  processed_count: number;
  synced_count: number;
  skipped_count: number;
  failed_count: number;
};

export type SubjectResyncResult = {
  subject_id: UUID;
  bangumi_id: number;
  title: string;
  subject_type: SubjectType;
  episode_synced: boolean;
  staff_count: number;
  character_count: number;
  related_subject_count: number;
};
