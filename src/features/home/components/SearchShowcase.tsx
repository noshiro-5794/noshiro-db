import { type FormEvent, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useI18n } from '@/features/i18n/use-i18n';
import { calendarImageOf, filterCalendarItems, flattenCalendarGroups, sortCalendarItems } from '@/features/search/calendar-search';
import {
  safetyOptions,
  subjectTypeOptions,
  type SafetyFilter,
  type SubjectTypeFilter,
} from '@/features/search/search-options';
import { subjectQueries } from '@/features/subjects/subject-queries';
import type { CalendarSubjectItem, SubjectSummary } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import type { RouteBackState } from '@/shared/navigation/route-state';
import { routeBackState } from '@/shared/navigation/route-state';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';

const coverPlaceholder = '/assets/placeholders/subject-cover.png';

function titleOf(item: CalendarSubjectItem, fallback: string) {
  return item.display_title || item.title || item.title_cn || fallback;
}

function subjectTitleOf(subject: SubjectSummary, fallback: string) {
  return subject.display_title || subject.title || subject.title_cn || fallback;
}

function subjectPosterOf(subject: SubjectSummary) {
  return subject.images?.poster || subject.images?.thumbnail || subject.image_thumbnail || subject.image || coverPlaceholder;
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

type ShowcasePosterProps = {
  badge?: string;
  poster: string;
  state?: RouteBackState;
  subtitle?: string;
  title: string;
  to: string;
};

function SearchPoster({ badge, poster, state, subtitle, title, to }: ShowcasePosterProps) {
  return (
    <Link className="group grid min-w-0 gap-2" state={state} to={to}>
      <div className="relative aspect-[2/3] overflow-hidden rounded-xl bg-[var(--color-surface-muted)] shadow-sm ring-1 ring-[var(--color-border)] transition group-hover:-translate-y-1 group-hover:shadow-lg group-hover:ring-[var(--color-accent-border)]">
        <img
          className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.035]"
          src={poster}
          alt={title}
          loading="lazy"
        />
        {badge ? (
          <div className="absolute left-2 top-2 rounded-full bg-black/55 px-2 py-1 text-[11px] font-semibold text-white backdrop-blur">
            {badge}
          </div>
        ) : null}
      </div>
      <span className="min-w-0">
        <span className="line-clamp-2 text-sm font-semibold leading-5 text-[var(--color-text)]">{title}</span>
        <span className="mt-1 line-clamp-1 text-xs text-[var(--color-text-muted)]">
          {subtitle}
        </span>
      </span>
    </Link>
  );
}

export function SearchShowcase() {
  const { locale, t } = useI18n();
  const location = useLocation();
  const [keyword, setKeyword] = useState('');
  const [submittedKeyword, setSubmittedKeyword] = useState('');
  const [subjectType, setSubjectType] = useState<SubjectTypeFilter>('');
  const [safety, setSafety] = useState<SafetyFilter>('safe');
  const calendarQuery = useQuery(subjectQueries.calendar());
  const isSearchingDatabase = Boolean(submittedKeyword.trim());
  const subjectQuery = useQuery({
    ...subjectQueries.list({
      keyword: submittedKeyword || undefined,
      subject_type: subjectType || undefined,
      nsfw: safety === 'safe' ? false : undefined,
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
  const isEmpty = isSearchingDatabase ? (subjectQuery.data?.results.length ?? 0) === 0 : calendarItems.length === 0;
  const subjectLinkState = routeBackState(location, t('nav.home'));

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
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
    <section className="mx-auto max-w-6xl px-4">
      <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-[var(--color-text)]">{t('search.title')}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--color-text-muted)]">{t('public.searchBody')}</p>
        </div>
        <Link className="text-sm font-semibold text-[var(--color-accent-strong)]" to={morePath}>
          {t('public.more')}
        </Link>
      </div>

      <form
        className="grid gap-3 rounded-2xl bg-[var(--color-surface-muted)] p-3 lg:grid-cols-[minmax(0,1.4fr)_150px_150px_auto]"
        onSubmit={handleSearchSubmit}
      >
        <label className="grid self-end">
          <span className="sr-only">{t('search.keyword')}</span>
          <Input
            value={keyword}
            placeholder={t('public.searchPlaceholder')}
            onChange={(event) => handleKeywordChange(event.target.value)}
          />
        </label>
        <div className="self-end">
          <FilterMenu
            label={t('search.type')}
            options={subjectTypeOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
            value={subjectType}
            onChange={setSubjectType}
          />
        </div>
        <div className="self-end">
          <FilterMenu
            label={t('search.safety')}
            options={safetyOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
            value={safety}
            onChange={setSafety}
          />
        </div>
        <Button className="self-end" size="lg" type="submit">
          {t('search.title')}
        </Button>
      </form>

      <div className="mt-5 grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
        {isSearchingDatabase
          ? (subjectQuery.data?.results ?? []).map((subject) => (
              <SearchPoster
                key={subject.id}
                poster={subjectPosterOf(subject)}
                state={subjectLinkState}
                subtitle={subject.display_subtitle || subject.subject_type}
                title={subjectTitleOf(subject, t('common.untitledSubject'))}
                to={routes.subject(subject.id)}
              />
            ))
          : calendarItems.map((item) => (
              <SearchPoster
                badge={new Intl.NumberFormat(locale, { notation: item.doing >= 10000 ? 'compact' : 'standard' }).format(item.doing)}
                key={item.subject_id}
                poster={calendarImageOf(item) || coverPlaceholder}
                state={subjectLinkState}
                subtitle={item.display_subtitle || item.subject_type}
                title={titleOf(item, t('common.untitledSubject'))}
                to={routes.subject(item.subject_id)}
              />
            ))}
      </div>

      {!isFetching && isEmpty ? (
        <div className="mt-5 rounded-2xl border border-dashed border-[var(--color-border)] p-8 text-center text-sm text-[var(--color-text-muted)]">
          {t('public.searchEmpty')}
        </div>
      ) : null}
    </section>
  );
}
