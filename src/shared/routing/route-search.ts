import { parseIntegerParam, parsePageParam, parseTextParam } from './search-params';

type RawSearch = Record<string, unknown>;

export function validateEmptySearch(): Record<never, never> {
  return {};
}

const collectionOrderings = [
  '-id',
  'id',
  'name',
  '-name',
  'simple_rating',
  '-simple_rating',
  'item_count',
  '-item_count',
] as const;
const contentStatuses = ['wish', 'doing', 'done', 'on_hold', 'drop'] as const;
const contentSubjectTypes = ['anime', 'galgame'] as const;
const libraryOrderings = [
  '-updated_at',
  '-created_at',
  '-rating',
  'rating',
  '-simple_rating',
  '-watch_end_date',
  '-watch_start_date',
] as const;
const publicSubjectOrderings = [
  '-id',
  'id',
  '-rating',
  'rating',
  '-simple_rating',
  'simple_rating',
  '-watch_end_date',
  'watch_end_date',
  '-watch_start_date',
  'watch_start_date',
] as const;
const reviewOrderings = ['-created_at', 'created_at', '-id', 'id'] as const;
const searchOrderings = ['-date', 'date', 'title', '-title'] as const;
const searchSeasons = ['winter', 'spring', 'summer', 'fall'] as const;
const searchPlatforms = ['TV', 'WEB', 'OVA', '剧场版', 'PC'] as const;
const episodeRanges = ['short', 'standard', 'long'] as const;
const activityScopes = ['all', 'mine'] as const;
const activityTypes = [
  'post_created',
  'user_subject_created',
  'user_subject_updated',
  'review_created',
  'collection_created',
  'collection_item_added',
  'comment_created',
  'user_followed',
] as const;

function rawString(value: unknown) {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  if (typeof value === 'boolean') return String(value);
  return undefined;
}

function optionalPage(value: unknown) {
  const raw = rawString(value);
  const parsed = parsePageParam(raw);
  return raw === undefined || parsed === 1 ? undefined : parsed;
}

function optionalPositiveInteger(value: unknown) {
  return parseIntegerParam(rawString(value), { min: 1 }) ?? undefined;
}

function optionalText(value: unknown, maxLength: number, trim = false) {
  const parsed = parseTextParam(rawString(value), { maxLength, trim });
  return parsed || undefined;
}

function optionalEnum<const Value extends string>(value: unknown, allowedValues: readonly Value[]) {
  const raw = rawString(value);
  return allowedValues.find((allowedValue) => allowedValue === raw);
}

export type CommentPageSearch = {
  activity_comments_page?: number | undefined;
  collection_comments_page?: number | undefined;
  post_comments_page?: number | undefined;
  review_comments_page?: number | undefined;
};

export function validateRootSearch(search: RawSearch): CommentPageSearch {
  return {
    activity_comments_page: optionalPage(search['activity_comments_page']),
    collection_comments_page: optionalPage(search['collection_comments_page']),
    post_comments_page: optionalPage(search['post_comments_page']),
    review_comments_page: optionalPage(search['review_comments_page']),
  };
}

export type PaginationSearch = { page?: number | undefined };

export function validatePaginationSearch(search: RawSearch): PaginationSearch {
  return { page: optionalPage(search['page']) };
}

export type CollectionsSearch = PaginationSearch & {
  collection?: number | undefined;
  keyword?: string | undefined;
  ordering?: (typeof collectionOrderings)[number] | undefined;
};

export function validateCollectionsSearch(search: RawSearch): CollectionsSearch {
  return {
    collection: optionalPositiveInteger(search['collection']),
    keyword: optionalText(search['keyword'], 200),
    ordering: optionalEnum(search['ordering'], collectionOrderings),
    page: optionalPage(search['page']),
  };
}

export type BookmarksSearch = PaginationSearch & {
  keyword?: string | undefined;
  target_type?: 'post' | 'review' | 'collection' | undefined;
};

export function validateBookmarksSearch(search: RawSearch): BookmarksSearch {
  return {
    keyword: optionalText(search['keyword'], 200),
    page: optionalPage(search['page']),
    target_type: optionalEnum(search['target_type'], ['post', 'review', 'collection']),
  };
}

export type CommunityPostsSearch = {
  scope?: (typeof activityScopes)[number] | undefined;
  type?: (typeof activityTypes)[number] | undefined;
};

export function validateCommunityPostsSearch(search: RawSearch): CommunityPostsSearch {
  return {
    scope: optionalEnum(search['scope'], activityScopes),
    type: optionalEnum(search['type'], activityTypes),
  };
}

export type LibrarySearch = PaginationSearch & {
  keyword?: string | undefined;
  ordering?: (typeof libraryOrderings)[number] | undefined;
  status?: (typeof contentStatuses)[number] | undefined;
  subject_type?: (typeof contentSubjectTypes)[number] | undefined;
  tag_id?: number | undefined;
};

export function validateLibrarySearch(search: RawSearch): LibrarySearch {
  return {
    keyword: optionalText(search['keyword'], 200),
    ordering: optionalEnum(search['ordering'], libraryOrderings),
    page: optionalPage(search['page']),
    status: optionalEnum(search['status'], contentStatuses),
    subject_type: optionalEnum(search['subject_type'], contentSubjectTypes),
    tag_id: optionalPositiveInteger(search['tag_id']),
  };
}

export type MeSearch = { year?: number | undefined };

export function validateMeSearch(search: RawSearch): MeSearch {
  const currentYear = new Date().getFullYear();
  const year = parseIntegerParam(rawString(search['year']), { min: 1970, max: currentYear + 1 });
  return { year: year ?? undefined };
}

export type ReviewsSearch = PaginationSearch & {
  keyword?: string | undefined;
  ordering?: (typeof reviewOrderings)[number] | undefined;
};

export function validateReviewsSearch(search: RawSearch): ReviewsSearch {
  return {
    keyword: optionalText(search['keyword'], 200),
    ordering: optionalEnum(search['ordering'], reviewOrderings),
    page: optionalPage(search['page']),
  };
}

export type ReviewEditorSearch = { subjectId?: string | undefined };

export function validateReviewEditorSearch(search: RawSearch): ReviewEditorSearch {
  const subjectId = optionalText(search['subjectId'], 36, true);
  return { subjectId };
}

export type SearchPageSearch = PaginationSearch & {
  episodes?: (typeof episodeRanges)[number] | undefined;
  keyword?: string | undefined;
  nsfw?: false | undefined;
  ordering?: (typeof searchOrderings)[number] | undefined;
  platform?: (typeof searchPlatforms)[number] | undefined;
  season?: (typeof searchSeasons)[number] | undefined;
  source_id?: string | undefined;
  subject_type?: (typeof contentSubjectTypes)[number] | undefined;
  year?: number | undefined;
};

export function validateSearchPageSearch(search: RawSearch): SearchPageSearch {
  const currentYear = new Date().getFullYear();
  return {
    episodes: optionalEnum(search['episodes'], episodeRanges),
    keyword: optionalText(search['keyword'], 200),
    nsfw: rawString(search['nsfw']) === 'false' ? false : undefined,
    ordering: optionalEnum(search['ordering'], searchOrderings),
    page: optionalPage(search['page']),
    platform: optionalEnum(search['platform'], searchPlatforms),
    season: optionalEnum(search['season'], searchSeasons),
    source_id: optionalText(search['source_id'], 64, true),
    subject_type: optionalEnum(search['subject_type'], contentSubjectTypes),
    year: parseIntegerParam(rawString(search['year']), { min: 1900, max: currentYear + 5 }) ?? undefined,
  };
}

type PublicContentSearch<Ordering extends string> = PaginationSearch & {
  keyword?: string | undefined;
  ordering?: Ordering | undefined;
};

export type PublicReviewsSearch = PublicContentSearch<(typeof reviewOrderings)[number]>;
export type PublicSubjectsSearch = PublicContentSearch<(typeof publicSubjectOrderings)[number]> & {
  status?: (typeof contentStatuses)[number] | undefined;
  subject_type?: (typeof contentSubjectTypes)[number] | undefined;
};
export type PublicCollectionsSearch = PublicContentSearch<(typeof collectionOrderings)[number]>;

function validatePublicContentSearch<Ordering extends string>(
  search: RawSearch,
  orderings: readonly Ordering[],
): PublicContentSearch<Ordering> {
  return {
    keyword: optionalText(search['keyword'], 200),
    ordering: optionalEnum(search['ordering'], orderings),
    page: optionalPage(search['page']),
  };
}

export function validatePublicReviewsSearch(search: RawSearch): PublicReviewsSearch {
  return validatePublicContentSearch(search, reviewOrderings);
}

export function validatePublicSubjectsSearch(search: RawSearch): PublicSubjectsSearch {
  return {
    ...validatePublicContentSearch(search, publicSubjectOrderings),
    status: optionalEnum(search['status'], contentStatuses),
    subject_type: optionalEnum(search['subject_type'], contentSubjectTypes),
  };
}

export function validatePublicCollectionsSearch(search: RawSearch): PublicCollectionsSearch {
  return validatePublicContentSearch(search, collectionOrderings);
}
