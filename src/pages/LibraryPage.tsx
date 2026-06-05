import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Search, SlidersHorizontal, Star, Tag as TagIcon, X } from 'lucide-react';
import { libraryMutations, libraryQueries, libraryQueryKeys } from '@/features/library/library-queries';
import type { Locale } from '@/features/i18n/messages';
import { useI18n } from '@/features/i18n/use-i18n';
import type { PrimarySubjectType, Tag, UserSubject, UserSubjectStatus } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { routeBackState } from '@/shared/navigation/route-state';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 12;
const coverPlaceholder = '/assets/placeholders/subject-cover.png';
const episodeUnit: Record<Locale, string> = {
  'zh-CN': '话',
  'en-US': 'episodes',
  'ja-JP': '話',
};

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function titleOf(item: UserSubject, fallback: string) {
  return item.subject.display_title || item.subject.title || item.subject.title_cn || fallback;
}

function subjectMetaOf(item: UserSubject, locale: Locale) {
  const subject = item.subject;
  const content = subject.content;
  const year = subject.year ?? subject.date?.slice(0, 4);
  const episodes = typeof content?.episodes === 'number' && content.episodes > 0 ? `${content.episodes} ${episodeUnit[locale]}` : '';
  const hasSubtitle = Boolean(subject.display_subtitle);
  return [
    subject.subject_type,
    subject.platform || '',
    !hasSubtitle && year ? String(year) : '',
    !hasSubtitle ? episodes : '',
  ].filter(Boolean).filter((value, index, array) => array.indexOf(value) === index).slice(0, 4);
}

function subjectSubtitleOf(item: UserSubject) {
  const subject = item.subject;
  return subject.display_subtitle || subject.display_meta?.join(' / ') || subject.date || subject.platform || subject.subject_type || '';
}

function SimpleRatingStars({ value, emptyLabel, ratingLabel }: { value: number | null; emptyLabel: string; ratingLabel: string }) {
  if (!value) return <span className="text-sm text-neutral-400">{emptyLabel}</span>;

  return (
    <span aria-label={`${ratingLabel} ${value}/5`} className="flex items-center gap-0.5">
      {Array.from({ length: 5 }, (_, index) => (
        <Star
          className={index < value ? 'size-4 fill-[var(--color-accent)] text-[var(--color-accent)]' : 'size-4 text-neutral-300 dark:text-neutral-700'}
          key={index}
        />
      ))}
    </span>
  );
}

export function LibraryPage() {
  const { locale, t } = useI18n();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const keyword = searchParams.get('keyword') ?? '';
  const status = (searchParams.get('status') ?? '') as UserSubjectStatus | '';
  const subjectType = (searchParams.get('subject_type') ?? '') as PrimarySubjectType | '';
  const tagId = searchParams.get('tag_id') ?? '';
  const ordering = searchParams.get('ordering') ?? '-updated_at';
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
  const [draftKeyword, setDraftKeyword] = useState(keyword);
  const [deleteTagTarget, setDeleteTagTarget] = useState<Tag | null>(null);
  const queryClient = useQueryClient();
  const statusOptions: Array<{ label: string; value: UserSubjectStatus | '' }> = [
    { label: t('status.all'), value: '' },
    { label: t('status.wish'), value: 'wish' },
    { label: t('status.doing'), value: 'doing' },
    { label: t('status.done'), value: 'done' },
    { label: t('status.onHold'), value: 'on_hold' },
    { label: t('status.drop'), value: 'drop' },
  ];
  const typeOptions: Array<{ label: string; value: PrimarySubjectType | '' }> = [
    { label: t('search.all'), value: '' },
    { label: t('search.anime'), value: 'anime' },
    { label: t('search.galgame'), value: 'galgame' },
  ];
  const orderingOptions = [
    { label: t('library.sortRecentlyUpdated'), value: '-updated_at' },
    { label: t('library.sortRecentlyAdded'), value: '-created_at' },
    { label: t('library.sortRatingHigh'), value: '-rating' },
    { label: t('library.sortRatingLow'), value: 'rating' },
    { label: t('library.sortSimpleRatingHigh'), value: '-simple_rating' },
    { label: t('library.sortRecentlyFinished'), value: '-watch_end_date' },
    { label: t('library.sortStartedRecently'), value: '-watch_start_date' },
  ];

  const query = useMemo(
    () => ({
      keyword: keyword || undefined,
      status: status || undefined,
      subject_type: subjectType || undefined,
      tag_id: tagId ? Number(tagId) : undefined,
      ordering,
      page: currentPage,
      page_size: pageSize,
    }),
    [currentPage, keyword, ordering, status, subjectType, tagId],
  );
  const libraryQuery = useQuery(libraryQueries.userSubjects(query));
  const tagsQuery = useQuery(libraryQueries.tags());
  const deleteTagMutation = useMutation({
    ...libraryMutations.deleteTag(),
    onSuccess: async () => {
      const deletedTagId = deleteTagTarget?.id;
      setDeleteTagTarget(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: libraryQueryKeys.tags() }),
        queryClient.invalidateQueries({ queryKey: libraryQueryKeys.userSubjects() }),
      ]);
      if (deletedTagId && tagId === String(deletedTagId)) {
        updateSearchParam('tag_id', '');
      }
    },
  });
  const totalCount = libraryQuery.data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const selectedTag = (tagsQuery.data?.results ?? []).find((tag) => String(tag.id) === tagId);

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  useEffect(() => {
    if (libraryQuery.data && currentPage > totalPages) {
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.set('page', String(totalPages));
        return nextParams;
      });
    }
  }, [currentPage, libraryQuery.data, setSearchParams, totalPages]);

  function updateSearchParam(key: string, value: string) {
    setSearchParams((currentParams) => {
      const nextParams = new URLSearchParams(currentParams);
      if (value) nextParams.set(key, value);
      else nextParams.delete(key);
      if (key !== 'page') nextParams.delete('page');
      return nextParams;
    });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateSearchParam('keyword', draftKeyword.trim());
  }

  function resetFilters() {
    setSearchParams(new URLSearchParams());
  }

  function statusLabel(statusValue: string) {
    return statusOptions.find((option) => option.value === statusValue)?.label ?? statusValue.replaceAll('_', ' ');
  }

  function goToPage(page: number) {
    updateSearchParam('page', String(Math.min(Math.max(page, 1), totalPages)));
  }

  return (
    <Page title={t('library.title')} eyebrow={t('nav.groupLibrary')}>
      <div className="grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="grid content-start gap-4">
          <section className="content-filter-panel">
            <div className="content-panel-title">
              <SlidersHorizontal className="size-4 text-neutral-400" />
              <h2>{t('library.status')}</h2>
            </div>
            <div className="grid gap-1">
              {statusOptions.map((option) => (
                <button
                  className={`content-filter-choice ${status === option.value ? 'is-active' : ''}`}
                  key={option.value || 'all'}
                  type="button"
                  onClick={() => updateSearchParam('status', option.value)}
                >
                  <span>{option.label}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="content-filter-panel">
            <div className="content-panel-title">
              <TagIcon className="size-4 text-neutral-400" />
              <h2>{t('library.tags')}</h2>
            </div>
            <div className="flex flex-wrap gap-2">
              {(tagsQuery.data?.results ?? []).map((tag) => {
                const isSelected = tagId === String(tag.id);
                return (
                  <span
                    className={`content-tag-chip ${isSelected ? 'is-active' : ''}`}
                    key={tag.id}
                  >
                    <button
                      className="px-3 py-1.5 transition hover:bg-white/60 dark:hover:bg-neutral-950/50"
                      type="button"
                      onClick={() => updateSearchParam('tag_id', isSelected ? '' : String(tag.id))}
                    >
                      {tag.name}
                    </button>
                    <button
                      aria-label={`${t('common.delete')} ${tag.name}`}
                      className="grid size-8 place-items-center border-l border-current/10 transition hover:bg-white/70 dark:hover:bg-neutral-950/60"
                      type="button"
                      onClick={() => setDeleteTagTarget(tag)}
                    >
                      <X className="size-3.5" />
                    </button>
                  </span>
                );
              })}
              {!tagsQuery.isLoading && (tagsQuery.data?.results.length ?? 0) === 0 ? (
                <span className="text-sm text-neutral-500 dark:text-neutral-400">{t('library.noTags')}</span>
              ) : null}
            </div>
          </section>
        </aside>

        <main className="grid content-start gap-5">
          <form className="content-toolbar" onSubmit={handleSubmit}>
            <div className="content-toolbar-grid is-library">
              <div className="content-toolbar-search">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-400" />
                <Input className="pl-9" value={draftKeyword} placeholder={t('library.searchPlaceholder')} onChange={(event) => setDraftKeyword(event.target.value)} />
              </div>
              <FilterMenu label={t('search.type')} options={typeOptions} value={subjectType} onChange={(value) => updateSearchParam('subject_type', value)} />
              <FilterMenu label={t('common.sort')} options={orderingOptions} value={ordering} onChange={(value) => updateSearchParam('ordering', value)} />
              <Button type="submit" variant="secondary">{t('common.search')}</Button>
            </div>
          </form>

          <div className="content-summary-bar">
            <div className="content-summary-count">
              <span className="content-summary-number">{totalCount}</span>
              <span>{t('common.subjects')}</span>
              {status ? <Badge variant="secondary">{statusLabel(status)}</Badge> : null}
              {subjectType ? <Badge variant="secondary">{subjectType}</Badge> : null}
              {selectedTag ? <Badge variant="secondary">{selectedTag.name}</Badge> : null}
              {keyword ? <Badge variant="secondary">{keyword}</Badge> : null}
            </div>
            <div className="content-summary-side">
              {libraryQuery.isFetching ? <span>{t('common.loading')}</span> : null}
              <span className="content-summary-page">{t('common.page')} {currentPage} / {totalPages}</span>
              {(status || subjectType || tagId || keyword || ordering !== '-updated_at') ? (
                <button className="font-semibold text-[var(--color-accent-strong)]" type="button" onClick={resetFilters}>{t('common.reset')}</button>
              ) : null}
            </div>
          </div>

          {libraryQuery.isLoading ? <LoadingState title={t('library.loading')} /> : null}
          {libraryQuery.isError ? <ErrorState title={t('library.errorTitle')} description={t('search.errorBody')} /> : null}
          {!libraryQuery.isLoading && !libraryQuery.isError && libraryQuery.data?.results.length === 0 ? (
            <EmptyState title={t('library.emptyTitle')} description={t('library.emptyBody')} />
          ) : null}

          <div className="content-list-panel">
            {(libraryQuery.data?.results ?? []).map((item) => (
              <Link
                className="library-list-item"
                key={item.id}
                state={routeBackState(location, t('nav.library'))}
                to={routes.subject(item.subject.id)}
              >
                <img
                  alt=""
                  className="h-28 w-[72px] rounded-lg bg-neutral-100 object-cover shadow-sm ring-1 ring-neutral-200 dark:bg-neutral-900 dark:ring-neutral-800 max-sm:h-[86px] max-sm:w-[58px]"
                  loading="lazy"
                  src={item.subject.image_thumbnail || item.subject.image || coverPlaceholder}
                />
                <span className="grid min-w-0 content-center gap-2">
                  <span className="grid min-w-0 gap-1">
                    <span className="line-clamp-1 font-semibold text-neutral-950 dark:text-white">{titleOf(item, t('common.untitledSubject'))}</span>
                    {subjectSubtitleOf(item) ? <span className="line-clamp-1 text-sm text-neutral-500 dark:text-neutral-400">{subjectSubtitleOf(item)}</span> : null}
                  </span>
                  <span className="flex min-w-0 flex-wrap gap-1.5">
                    {subjectMetaOf(item, locale).map((meta) => (
                      <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-500 dark:bg-neutral-900 dark:text-neutral-400" key={meta}>
                        {meta}
                      </span>
                    ))}
                  </span>
                  {item.comment ? (
                    <span className="line-clamp-1 text-sm font-medium text-neutral-600 dark:text-neutral-300">{item.comment}</span>
                  ) : item.subject.description_excerpt ? (
                    <span className="line-clamp-1 text-sm leading-6 text-neutral-500 dark:text-neutral-400">{item.subject.description_excerpt}</span>
                  ) : null}
                  {(item.watch_start_date || item.watch_end_date) ? (
                    <span className="text-xs text-neutral-400">
                      {[item.watch_start_date ? `${t('library.started')} ${formatDate(item.watch_start_date)}` : '', item.watch_end_date ? `${t('library.finished')} ${formatDate(item.watch_end_date)}` : ''].filter(Boolean).join(' · ')}
                    </span>
                  ) : null}
                </span>
                <span className="grid justify-items-end gap-2 self-center max-sm:col-start-2 max-sm:justify-items-start">
                  <Badge variant="secondary">{statusLabel(item.status)}</Badge>
                  <span className="grid justify-items-end gap-1 text-sm text-neutral-500 dark:text-neutral-400 max-sm:justify-items-start">
                    {item.rating ? <strong className="font-semibold text-neutral-950 dark:text-white">{item.rating}</strong> : null}
                    <SimpleRatingStars emptyLabel={t('library.noSimpleRating')} ratingLabel={t('library.simpleRatingLabel')} value={item.simple_rating} />
                  </span>
                  {item.updated_at ? <span className="text-xs text-neutral-400">{formatDate(item.updated_at)}</span> : null}
                </span>
              </Link>
            ))}
          </div>

          <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
        </main>
      </div>

      <Dialog open={Boolean(deleteTagTarget)} onOpenChange={(open) => !open && setDeleteTagTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('library.deleteTagTitle')}</DialogTitle>
            <DialogDescription>
              {t('library.deleteTagBody')} {deleteTagTarget?.name ? `"${deleteTagTarget.name}"` : ''}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setDeleteTagTarget(null)}>{t('common.cancel')}</Button>
            <Button disabled={deleteTagMutation.isPending} type="button" onClick={() => deleteTagTarget && deleteTagMutation.mutate(deleteTagTarget.id)}>
              {t('common.delete')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </Page>
  );
}
