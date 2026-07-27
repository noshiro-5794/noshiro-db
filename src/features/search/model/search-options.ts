import type { MessageKey } from '@/shared/i18n';
import type { SubjectOrdering } from '@/entities/subject';
import type { PrimarySubjectType } from '@/shared/api';

export type SubjectTypeFilter = PrimarySubjectType | '';
export type SafetyFilter = 'safe' | 'all';
export type SeasonFilter = '' | 'winter' | 'spring' | 'summer' | 'fall';
export type PlatformFilter = '' | 'TV' | 'WEB' | 'OVA' | '剧场版' | 'PC';
export type EpisodeRangeFilter = '' | 'short' | 'standard' | 'long';

export const subjectTypeOptions: Array<{ value: SubjectTypeFilter; labelKey: MessageKey }> = [
  { value: '', labelKey: 'search.all' },
  { value: 'anime', labelKey: 'search.anime' },
  { value: 'galgame', labelKey: 'search.galgame' },
];

export const orderingOptions: Array<{ value: SubjectOrdering; labelKey: MessageKey }> = [
  { value: '-date', labelKey: 'search.latest' },
  { value: 'date', labelKey: 'search.oldest' },
  { value: 'title', labelKey: 'search.titleAsc' },
  { value: '-title', labelKey: 'search.titleDesc' },
];

export const safetyOptions: Array<{ value: SafetyFilter; labelKey: MessageKey }> = [
  { value: 'safe', labelKey: 'search.safeOnly' },
  { value: 'all', labelKey: 'search.includeNsfw' },
];

export const seasonOptions: Array<{ value: SeasonFilter; labelKey: MessageKey }> = [
  { value: '', labelKey: 'search.all' },
  { value: 'winter', labelKey: 'search.seasonWinter' },
  { value: 'spring', labelKey: 'search.seasonSpring' },
  { value: 'summer', labelKey: 'search.seasonSummer' },
  { value: 'fall', labelKey: 'search.seasonFall' },
];

export const platformOptions: Array<{ value: PlatformFilter; label: string }> = [
  { value: '', label: 'All' },
  { value: 'TV', label: 'TV' },
  { value: 'WEB', label: 'WEB' },
  { value: 'OVA', label: 'OVA' },
  { value: '剧场版', label: 'Movie' },
  { value: 'PC', label: 'PC' },
];

export const episodeRangeOptions: Array<{ value: EpisodeRangeFilter; labelKey: MessageKey }> = [
  { value: '', labelKey: 'search.all' },
  { value: 'short', labelKey: 'search.episodesShort' },
  { value: 'standard', labelKey: 'search.episodesStandard' },
  { value: 'long', labelKey: 'search.episodesLong' },
];
