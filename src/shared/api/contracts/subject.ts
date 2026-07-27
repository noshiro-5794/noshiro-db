import type { DateString, ISODateString, OpenString, UUID } from './common';

export type PrimarySubjectType = 'anime' | 'galgame';

export type SubjectType = PrimarySubjectType | (string & {});

export type WeekdayEn = 'Mon' | 'Tue' | 'Wed' | 'Thu' | 'Fri' | 'Sat' | 'Sun';

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
  direction?: 'outgoing' | 'incoming' | OpenString;
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
  image_url?: string | null;
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
