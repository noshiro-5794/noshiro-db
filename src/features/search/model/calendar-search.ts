import type { SubjectOrdering } from '@/entities/subject';
import type { CalendarGroup, CalendarSubjectItem, SubjectSummary, WeekdayEn } from '@/shared/api';
import type { SafetyFilter, SubjectTypeFilter } from './search-options';

export type CalendarSearchFilters = {
  keyword?: string;
  ordering?: SubjectOrdering;
  safety?: SafetyFilter;
  subjectType?: SubjectTypeFilter;
  weekday?: WeekdayEn | '';
};

function itemTitle(item: CalendarSubjectItem) {
  return item.display_title || item.title || item.title_cn || 'Untitled';
}

export function calendarImageOf(item: CalendarSubjectItem) {
  const images =
    'images' in item && typeof item.images === 'object' && item.images
      ? (item.images as { original?: string | null; poster?: string | null; thumbnail?: string | null })
      : null;
  const image = 'image' in item && typeof item.image === 'string' ? item.image : null;

  return (
    item.image_url || item.image_thumbnail || images?.poster || images?.thumbnail || images?.original || image || null
  );
}

export function flattenCalendarGroups(groups: CalendarGroup[] = []) {
  return groups.flatMap((group) => group.items);
}

export function filterCalendarItems(items: CalendarSubjectItem[], filters: CalendarSearchFilters) {
  const keyword = filters.keyword?.trim().toLowerCase();

  return items.filter((item) => {
    if (filters.subjectType && item.subject_type !== filters.subjectType) {
      return false;
    }
    if (filters.safety === 'safe' && item.nsfw) {
      return false;
    }
    if (filters.weekday && item.weekday_en !== filters.weekday) {
      return false;
    }
    if (keyword) {
      const title = `${item.title} ${item.title_cn ?? ''}`.toLowerCase();
      return title.includes(keyword);
    }
    return true;
  });
}

export function sortCalendarItems(items: CalendarSubjectItem[], ordering: SubjectOrdering = '-date') {
  const nextItems = [...items];

  if (ordering === 'title' || ordering === '-title') {
    nextItems.sort((a, b) => itemTitle(a).localeCompare(itemTitle(b)));
    return ordering === '-title' ? nextItems.reverse() : nextItems;
  }

  nextItems.sort((a, b) => b.doing - a.doing || itemTitle(a).localeCompare(itemTitle(b)));
  return nextItems;
}

export function calendarItemToSubjectSummary(item: CalendarSubjectItem): SubjectSummary {
  const image = calendarImageOf(item);

  return {
    id: item.subject_id,
    subject_type: item.subject_type,
    title: item.title,
    title_cn: item.title_cn,
    display_title: item.display_title || item.title || item.title_cn || 'Untitled',
    title_original: item.title,
    title_localized: item.title_cn,
    display_meta: item.display_meta,
    display_subtitle: item.display_subtitle,
    date: item.date ?? null,
    platform: item.platform,
    nsfw: item.nsfw,
    image,
    image_thumbnail: image,
    images: {
      poster: image,
      thumbnail: image,
      original: image,
    },
  };
}
