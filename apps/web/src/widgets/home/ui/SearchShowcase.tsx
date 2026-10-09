import { type SyntheticEvent, useMemo, useState } from 'react';
import { useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { useI18n } from '@/shared/i18n';
import { subjectKindLabel } from '@/shared/i18n/subject-labels';
import { calendarImageOf, filterCalendarItems, flattenCalendarGroups, sortCalendarItems } from '@/features/search';
import { safetyOptions, subjectTypeOptions, type SafetyFilter, type SubjectTypeFilter } from '@/features/search';
import { subjectQueries, SubjectPosterCard } from '@/entities/subject';
import type { CalendarSubjectItem, SubjectSummary } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { routeBackState } from '@/shared/routing/route-state';
import { Button } from '@/shared/ui/Button';
import { DataToolbar, DataToolbarPrimary, DataToolbarRow, SearchField } from '@/shared/ui/DataView';
import { ErrorState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { LandingSection } from './LandingSection';

function titleOf(item: CalendarSubjectItem, fallback: string) {
  return item.display_title || item.title || item.title_cn || fallback;
}

function subjectTitleOf(subject: SubjectSummary, fallback: string) {
  return subject.display_title || subject.title || subject.title_cn || fallback;
}

function subjectPosterOf(subject: SubjectSummary) {
  return subject.images?.poster || subject.images?.thumbnail || subject.image_thumbnail || subject.image || null;
}

function buildSearchPath({
  keyword,
  safety,
  subjectType,
}: {
  keyword: string;
  safety: SafetyFilter;
  subjectType: SubjectTypeFilter;
}) {
  const params = new URLSearchParams();
  const trimmedKeyword = keyword.trim();

  if (trimmedKeyword) {
    params.set('keyword', trimmedKeyword);
  }
  if (subjectType) {
    params.set('subject_type', subjectType);
  }
  if (safety === 'safe') {
    params.set('nsfw', 'false');
  }

  const query = params.toString();
  return query ? `${routes.search}?${query}` : routes.search;
}

export function SearchShowcase() {
  const { t } = useI18n();
  const location = useLocation();
  const [keyword, setKeyword] = useState('');
  const [submittedKeyword, setSubmittedKeyword] = useState('');
  const [subjectType, setSubjectType] = useState<SubjectTypeFilter>('');
  const [safety, setSafety] = useState<SafetyFilter>('safe');
  const calendarQuery = useQuery(subjectQueries.calendar());
  const isSearchingDatabase = Boolean(submittedKeyword.trim());
  const subjectQuery = useQuery({
    ...subjectQueries.list({
      ...(submittedKeyword ? { keyword: submittedKeyword } : {}),
      ...(subjectType ? { subject_type: subjectType } : {}),
      ...(safety === 'safe' ? { nsfw: false } : {}),
      page: 1,
      page_size: 12,
    }),
    enabled: isSearchingDatabase,
  });

  const calendarItems = useMemo(() => {
    const items = flattenCalendarGroups(calendarQuery.data);
    const filteredItems = filterCalendarItems(items, {
      safety,
      subjectType,
    });
    return sortCalendarItems(filteredItems).slice(0, 12);
  }, [calendarQuery.data, safety, subjectType]);

  const morePath = buildSearchPath({ keyword: submittedKeyword || keyword, safety, subjectType });
  const isFetching = isSearchingDatabase ? subjectQuery.isFetching : calendarQuery.isFetching;
  const isError = isSearchingDatabase ? subjectQuery.isError : calendarQuery.isError;
  const isEmpty = isSearchingDatabase ? (subjectQuery.data?.results.length ?? 0) === 0 : calendarItems.length === 0;
  const subjectLinkState = routeBackState(location, t('nav.home'));

  function handleSearchSubmit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    setSubmittedKeyword(keyword.trim());
  }

  function handleKeywordChange(nextKeyword: string) {
    setKeyword(nextKeyword);
    if (!nextKeyword.trim()) {
      setSubmittedKeyword('');
    }
  }

  return (
    <LandingSection
      action={{ label: t('public.more'), to: morePath }}
      className="scroll-mt-24 pt-20 sm:pt-28"
      note={t('public.searchBody')}
      title={t('public.startSearch')}
    >
      <DataToolbar onSubmit={handleSearchSubmit}>
        <DataToolbarRow className="lg:grid-cols-[minmax(0,1.4fr)_150px_150px_auto]">
          <DataToolbarPrimary>
            <SearchField
              aria-label={t('search.keyword')}
              maxLength={200}
              placeholder={t('public.searchPlaceholder')}
              size="lg"
              value={keyword}
              onChange={(event) => {
                handleKeywordChange(event.target.value);
              }}
            />
          </DataToolbarPrimary>
          <FilterMenu
            label={t('search.type')}
            options={subjectTypeOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
            size="lg"
            value={subjectType}
            onChange={setSubjectType}
          />
          <FilterMenu
            label={t('search.safety')}
            options={safetyOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
            size="lg"
            value={safety}
            onChange={setSafety}
          />
          <Button size="lg" type="submit">
            {t('search.title')}
          </Button>
        </DataToolbarRow>
      </DataToolbar>

      <div className="mt-5 grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
        {isSearchingDatabase
          ? (subjectQuery.data?.results ?? []).map((subject) => (
              <SubjectPosterCard
                key={subject.id}
                poster={subjectPosterOf(subject)}
                seed={subject.id}
                state={subjectLinkState}
                subtitle={subjectKindLabel(subject.display_subtitle || subject.subject_type, t)}
                title={subjectTitleOf(subject, t('common.untitledSubject'))}
                to={routes.entity(subject.id)}
              />
            ))
          : calendarItems.map((item) => (
              <SubjectPosterCard
                key={item.subject_id}
                poster={calendarImageOf(item)}
                seed={item.subject_id}
                state={subjectLinkState}
                subtitle={subjectKindLabel(item.display_subtitle || item.subject_type, t)}
                title={titleOf(item, t('common.untitledSubject'))}
                to={routes.entity(item.subject_id)}
              />
            ))}
      </div>

      {isError ? (
        <div className="mt-5">
          <ErrorState title={t('search.errorTitle')} description={t('search.errorBody')} />
        </div>
      ) : null}
      {!isFetching && !isError && isEmpty ? (
        <div className="mt-5 rounded-[var(--ui-radius-surface)] border border-dashed border-[var(--ui-border)] p-8 text-center text-sm text-[var(--ui-text-muted)]">
          {t('public.searchEmpty')}
        </div>
      ) : null}
    </LandingSection>
  );
}
