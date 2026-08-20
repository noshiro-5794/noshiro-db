import type { ISODateString, UUID } from './common';

export type EntityKind =
  | 'work'
  | 'release'
  | 'episode'
  | 'contributor'
  | 'character'
  | 'unclassified'
  | (string & {});

export type EntityLifecycle = 'active' | 'merged' | 'retired' | (string & {});

export type EntityAudience = 'unknown' | 'general' | 'adult' | (string & {});

export type WorkType =
  | 'anime'
  | 'galgame'
  | 'manga'
  | 'novel'
  | 'game'
  | 'music'
  | 'other'
  | 'unclassified'
  | (string & {});

export type EntitySafety = 'safe' | 'suggestive' | 'explicit' | 'unknown' | (string & {});

export type EntityNameKind =
  | 'original'
  | 'official'
  | 'alias'
  | 'short'
  | 'romanized'
  | 'translated'
  | (string & {});

export type EntityFactStatus = 'candidate' | 'selected' | 'rejected' | (string & {});

export type DatePrecision = 'day' | 'month' | 'year' | 'range' | 'unknown' | (string & {});

export type FieldProvenance = {
  provider: string;
  namespace: string;
  external_id: string;
  observation_id: UUID | null;
  revision_id: UUID | null;
  observed_at: ISODateString | null;
};

export type FactEvidence = {
  provider: string;
  namespace: string;
  external_id: string;
  observation_id: UUID | null;
  revision_id: UUID | null;
  observed_at: ISODateString | null;
  json_pointer: string;
};

export type EntityMedia = {
  url: string;
  purpose: string;
  safety: EntitySafety;
  provenance: FieldProvenance | null;
};

export type EntityName = {
  text: string;
  language: string;
  script: string;
  region: string;
  kind: EntityNameKind;
  is_official: boolean;
  is_original: boolean;
  is_machine_generated: boolean;
  is_reviewed: boolean;
  provenance: FieldProvenance | null;
};

export type EntityDescription = {
  text: string;
  language: string;
  is_official: boolean;
  is_machine_generated: boolean;
  is_reviewed: boolean;
  spoiler_level: number;
  safety: EntitySafety;
  provenance: FieldProvenance | null;
};

export type EntityFact = {
  predicate: string;
  value: unknown;
  language: string;
  status: EntityFactStatus;
  confidence: string;
  spoiler_level: number;
  safety: EntitySafety;
  is_machine_generated: boolean;
  evidence: FactEvidence[];
};

export type EntityExternalLink = {
  url: string;
  label: string;
  link_type: string;
  provenance: FieldProvenance | null;
};

export type EntityContentRating = {
  system: string;
  value: string;
  region: string;
  minimum_age: number | null;
  provenance: FieldProvenance;
};

export type EntitySource = {
  provider: string;
  namespace: string;
  external_id: string;
  url: string;
  mapping_kind: string;
  method: string;
  confidence: string;
  last_seen_at: ISODateString | null;
};

export type EntitySummary = {
  id: UUID;
  entity_type: EntityKind;
  lifecycle: EntityLifecycle;
  audience: EntityAudience;
  work_type: WorkType | null;
  display_name: string;
  collections: string[];
  media: EntityMedia[];
};

export type EntityDetail = EntitySummary & {
  names: EntityName[];
  descriptions: EntityDescription[];
  facts: EntityFact[];
  external_links: EntityExternalLink[];
  content_ratings: EntityContentRating[];
  sources: EntitySource[];
};

export type EntityCredit = {
  role: string;
  credited_as: string;
  contributor: EntitySummary;
  provenance: FieldProvenance | null;
};

export type EntityCharacter = {
  role: string;
  spoiler_level: number;
  character: EntitySummary;
  provenance: FieldProvenance | null;
};

export type EntityEpisode = {
  id: UUID;
  title: string;
  title_cn: string;
  type: string;
  number: string;
  sort: string;
  disc: number;
  duration: string;
  raw_duration: string;
  air_date: string;
  comment_count: number;
  description: string;
  provenance: FieldProvenance | null;
};

export type EntityRelation = {
  relation_type: string;
  target: EntitySummary;
  qualifiers: unknown;
  evidence: FactEvidence[];
};

export type EntityRelease = {
  role: string;
  release: EntitySummary;
  date_start: string | null;
  date_end: string | null;
  date_precision: DatePrecision;
  date_raw: string;
  platform: string;
  region: string;
  evidence: FactEvidence[];
};

export type EntityMetric = {
  metric: string;
  value: string;
  sample_size: number;
  observed_at: ISODateString;
  provider: string;
};

export type EntityEvidence = {
  provider: string;
  namespace: string;
  external_id: string;
  revision_id: UUID;
  observed_at: ISODateString;
};

export type CalendarEvent = {
  id: number;
  work_id: UUID;
  episode_id: UUID | null;
  starts_at: ISODateString | null;
  timezone: string;
  region: string;
  weekday: number | null;
  precision: string;
  raw_value: string;
  provenance: FieldProvenance | null;
};

export type IndexCollection = {
  slug: string;
  name: string;
};
