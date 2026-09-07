import type { DateString, ISODateString, UUID } from './common';
import type {
  EntityDetail,
  EntitySummary,
  WorkType,
  EntityCharacter,
  EntityCredit,
  EntityEpisode,
  EntityRelease,
  FactEvidence,
} from './entity';

export type {
  CalendarEvent,
  EntityAudience,
  EntityCharacter,
  EntityContentRating,
  EntityCredit,
  EntityDescription,
  EntityDetail,
  EntityEpisode,
  EntityEvidence,
  EntityExternalLink,
  EntityFact,
  EntityKind,
  EntityLifecycle,
  EntityMedia,
  EntityMetric,
  EntityName,
  EntityRelation,
  EntityRelease,
  EntitySafety,
  EntitySource,
  EntitySummary,
  FactEvidence,
  FieldProvenance,
  IndexCollection,
  WorkType,
} from './entity';

export type PrimarySubjectType = Extract<WorkType, 'anime' | 'galgame'>;
export type SubjectType = string;

export type WeekdayEn = 'Mon' | 'Tue' | 'Wed' | 'Thu' | 'Fri' | 'Sat' | 'Sun';

export type SubjectImages = {
  poster?: string | null;
  thumbnail?: string | null;
  original?: string | null;
};

export type SubjectSummary = EntitySummary & {
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
  images?: SubjectImages;
  image_original?: string | null;
  description?: string;
  description_excerpt?: string;
  source?: {
    provider?: string;
    id?: string;
  };
  source_id?: string | number;
  content?: {
    series?: boolean;
    episodes?: number | null;
    volumes?: number | null;
  };
  updated_at?: ISODateString;
  created_at?: ISODateString;
};

export type SubjectDetail = EntityDetail &
  SubjectSummary & {
    summary?: string;
    episode_count: number;
    staff_count: number;
    character_count: number;
    infobox?: unknown;
    tags?: string[];
  };

export type SubjectEpisode = EntityEpisode & {
  ep_num: number | null;
  date: DateString | null;
};

export type SubjectStaff = EntitySummary & {
  name: string;
  name_cn?: string | null;
  role?: string | null;
  description?: string;
  gender?: string;
  birth?: unknown;
  career?: unknown;
  image?: string | null;
  images?: SubjectImages;
  image_original?: string | null;
  image_thumbnail?: string | null;
  infobox?: unknown;
  type?: string | null;
};

export type SubjectCharacter = EntitySummary & {
  name: string;
  name_cn?: string | null;
  role?: string | null;
  description?: string;
  gender?: string;
  birth?: unknown;
  blood_type?: string;
  image?: string | null;
  images?: SubjectImages;
  image_original?: string | null;
  image_thumbnail?: string | null;
  infobox?: unknown;
  type?: string | null;
  actors?: SubjectStaff[];
};

export type SubjectRelation = {
  direction?: string;
  relation: string;
  subject: SubjectSummary;
  evidence?: FactEvidence[];
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
  image?: string | null;
  image_thumbnail: string | null;
  images?: SubjectImages;
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

export type EntityStaff = EntityCredit;
export type EntityStaffCharacter = EntityCharacter;
export type EntityReleaseRelation = EntityRelease;
