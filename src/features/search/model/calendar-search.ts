import type { SubjectOrdering } from '@/entities/subject';
import type { CalendarGroup, CalendarSubjectItem, WeekdayEn } from '@/shared/api';
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
  return (
    item.image_url ||
    item.image_thumbnail ||
    item.images?.poster ||
    item.images?.thumbnail ||
    item.images?.original ||
    item.image ||
    null
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
