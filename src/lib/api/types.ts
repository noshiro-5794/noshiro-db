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
  | 'post_created'
  | 'user_subject_created'
  | 'user_subject_updated'
  | 'review_created'
  | 'collection_created'
  | 'collection_item_added'
  | 'comment_created'
  | 'user_followed'
  | (string & {});
export type CommunityVisibility = 'public' | 'followers' | 'private' | (string & {});
export type CommunityFeedPolicy = 'hidden' | 'normal' | 'featured' | (string & {});
export type CommunityPostType = 'status' | 'subject' | (string & {});
export type CommunityTargetType = 'activity' | 'post' | 'comment' | 'review' | 'collection' | (string & {});
export type CommunityReactionType = 'like' | (string & {});
export type CommunityReportReason = 'spam' | 'harassment' | 'spoiler' | 'illegal' | 'other' | (string & {});
export type CommunityReportStatus = 'pending' | 'accepted' | 'rejected' | (string & {});

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
  language?: 'auto' | 'en-US' | 'zh-CN' | 'ja-JP';
  appearance?: 'auto' | 'light' | 'dark';
  theme_color: string | null;
};

export type ProfileStats = {
  year: number;
  available_years: number[];
  totals: {
    subjects: number;
    reviews: number;
    collections: number;
    marks_in_year: number;
  };
  mark_calendar: Array<{
    date: DateString;
    count: number;
  }>;
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
  title_original?: string;
  title_localized?: string | null;
  display_title?: string;
  display_meta?: string[];
  display_subtitle?: string;
  subject_type: SubjectType;
  date: DateString | null;
  year?: number | null;
  platform: string | null;
  nsfw: boolean;
  image?: string | null;
  image_thumbnail?: string | null;
  images?: {
    poster?: string | null;
    thumbnail?: string | null;
    original?: string | null;
  };
  image_original?: string | null;
  description?: string;
  description_excerpt?: string;
  source?: {
    provider?: string;
    id?: string;
  };
  content?: {
    series?: boolean;
    episodes?: number | null;
    volumes?: number | null;
  };
  updated_at?: ISODateString;
  created_at?: ISODateString;
} & Record<string, unknown>;

export type SubjectDetail = SubjectSummary & {
  summary?: string;
  description?: string;
  image_original?: string | null;
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
  duration?: string | null;
  date: DateString | null;
  description?: string;
} & Record<string, unknown>;

export type SubjectStaff = {
  id: number;
  name: string;
  name_cn?: string | null;
  role?: string | null;
  description?: string;
  gender?: string;
  birth?: unknown;
  career?: unknown;
  image_original?: string | null;
  image_thumbnail?: string | null;
  infobox?: unknown;
  type?: string | null;
} & Record<string, unknown>;

export type SubjectCharacter = {
  id: number;
  name: string;
  name_cn?: string | null;
  role?: string | null;
  description?: string;
  gender?: string;
  birth?: unknown;
  blood_type?: string;
  image_original?: string | null;
  image_thumbnail?: string | null;
  infobox?: unknown;
  type?: string | null;
  actors?: SubjectStaff[];
} & Record<string, unknown>;

export type SubjectRelation = {
  direction?: 'outgoing' | 'incoming' | string;
  relation: string;
  subject: SubjectSummary;
} & Record<string, unknown>;

export type SubjectRelationList = {
  items?: SubjectRelation[];
  outgoing: SubjectRelation[];
  incoming: SubjectRelation[];
  outgoing_count?: number;
  incoming_count?: number;
};

export type CalendarSubjectItem = {
  subject_id: UUID;
  subject_type: SubjectType;
  title: string;
  title_cn: string | null;
  display_title?: string;
  display_meta?: string[];
  display_subtitle?: string;
  date?: DateString | null;
  image_thumbnail: string | null;
  platform: string | null;
  nsfw: boolean;
  weekday_en: WeekdayEn;
  doing: number;
};

export type CalendarGroup = {
  weekday: {
    id: number | null;
    en: WeekdayEn;
  };
  items: CalendarSubjectItem[];
};

export type UserSubject = {
  id: number;
  status: UserSubjectStatus;
  simple_rating: number | null;
  rating: DecimalString | null;
  comment: string;
  watch_start_date: DateString | '';
  watch_end_date: DateString | '';
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
  user_subject: Pick<UserSubject, 'id' | 'status' | 'simple_rating' | 'rating' | 'comment' | 'watch_start_date' | 'watch_end_date' | 'is_public'>;
  subject: SubjectSummary;
  order: number;
  relation: string;
} & Record<string, unknown>;

export type FollowRelation = {
  user: PublicUserSummary;
  followed_at: ISODateString;
};

export type CommunityPostSummary = {
  id: number;
  post_type?: CommunityPostType;
  content: string;
  visibility: CommunityVisibility;
  feed_policy?: CommunityFeedPolicy;
  is_spoiler: boolean;
  is_nsfw: boolean;
  is_pinned?: boolean;
  is_locked?: boolean;
  reply_count?: number;
  reaction_count?: number;
  last_activity_at?: ISODateString;
  created_at?: ISODateString;
  updated_at?: ISODateString;
  author?: PublicUserSummary | null;
  subject?: Pick<SubjectSummary, 'id' | 'title' | 'title_cn' | 'subject_type' | 'image_thumbnail' | 'nsfw'> | null;
  viewer_state?: {
    has_liked: boolean;
    has_bookmarked: boolean;
    is_following_author: boolean;
  };
} & Record<string, unknown>;

export type CommunityCommentSummary = {
  id: number;
  parent_id?: number | null;
  target?: {
    type: CommunityTargetType;
    id: number;
  } | null;
  content: string;
  visibility: CommunityVisibility;
  is_spoiler: boolean;
  is_hidden?: boolean;
  is_locked?: boolean;
  reply_count?: number;
  reaction_count?: number;
  created_at?: ISODateString;
  updated_at?: ISODateString;
  author?: PublicUserSummary | null;
  viewer_state?: {
    has_liked: boolean;
    is_following_author: boolean;
  };
} & Record<string, unknown>;

export type Activity = {
  id: number;
  activity_type: ActivityType;
  created_at: ISODateString;
  reaction_count?: number;
  message?: string;
  visibility?: CommunityVisibility;
  feed_policy?: CommunityFeedPolicy;
  group_key?: string;
  dedupe_key?: string;
  user?: PublicUserSummary;
  subject?: SubjectSummary;
  review?: Review;
  collection?: Collection;
  collection_item?: CollectionItem;
  post?: CommunityPostSummary;
  comment?: CommunityCommentSummary;
  target_user?: PublicUserSummary;
  viewer_state?: {
    has_liked: boolean;
  };
} & Record<string, unknown>;

export type CommunityReaction = {
  id: number;
  target_type: CommunityTargetType;
  target_id: number;
  reaction_type: CommunityReactionType;
  created_at: ISODateString;
};

export type CommunityBookmark = {
  id: number;
  target_type: CommunityTargetType;
  target_id: number;
  target?: {
    type: 'post' | 'review' | 'collection' | (string & {});
    id: number;
    title?: string;
    body?: string;
    author?: PublicUserSummary | null;
    subject?: Pick<SubjectSummary, 'id' | 'title' | 'title_cn' | 'subject_type' | 'image_thumbnail'> | null;
    is_spoiler?: boolean;
    simple_rating?: number | null;
    created_at?: ISODateString;
  } | null;
  created_at: ISODateString;
};

export type CommunityNotification = {
  id: number;
  notification_type: string;
  actor: PublicUserSummary | null;
  target: ({
    type: CommunityTargetType;
    id: number;
    author?: PublicUserSummary | null;
    owner?: PublicUserSummary | null;
    user?: PublicUserSummary | null;
    target_user?: PublicUserSummary | null;
    parent_id?: number | null;
    post?: {
      type: 'post';
      id: number;
      author?: PublicUserSummary | null;
    };
    review?: {
      type: 'review';
      id: number;
      author?: PublicUserSummary | null;
    };
    collection?: {
      type: 'collection';
      id: number;
      owner?: PublicUserSummary | null;
    };
    activity?: {
      type: 'activity';
      id: number;
      user?: PublicUserSummary | null;
    };
    subject?: {
      id: UUID;
    };
    comment?: {
      type: 'comment';
      id: number;
    };
  } & Record<string, unknown>) | null;
  metadata: Record<string, unknown>;
  is_read: boolean;
  read_at: ISODateString | null;
  created_at: ISODateString;
};

export type CommunityNotificationUnreadCount = {
  unread_count: number;
};

export type CommunityRelationship = {
  user: PublicUserSummary;
  reason: string;
  created_at: ISODateString;
};

export type CommunityReport = {
  id: number;
  reason: CommunityReportReason;
  description: string;
  status: CommunityReportStatus;
  reporter: PublicUserSummary;
  reported_user: PublicUserSummary | null;
  target: {
    type: CommunityTargetType;
    id: number;
  } | null;
  resolved_by: PublicUserSummary | null;
  resolved_at: ISODateString | null;
  created_at: ISODateString;
};

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
