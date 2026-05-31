import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { tagsApi } from '@/features/library/api';
import { libraryQueries, libraryQueryKeys } from '@/features/library/library-queries';
import type { PrimarySubjectType, UserSubjectStatus } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';

const pageSize = 20;
const coverPlaceholder = '/assets/placeholders/subject-cover.png';

type PaginationItem = number | 'ellipsis';

const statusOptions: Array<{ label: string; value: UserSubjectStatus | '' }> = [
  { label: 'All status', value: '' },
  { label: 'Wish', value: 'wish' },
  { label: 'Watching', value: 'doing' },
  { label: 'Completed', value: 'done' },
  { label: 'On hold', value: 'on_hold' },
  { label: 'Dropped', value: 'drop' },
];

const typeOptions: Array<{ label: string; value: PrimarySubjectType | '' }> = [
  { label: 'All types', value: '' },
  { label: 'Anime', value: 'anime' },
  { label: 'Galgame', value: 'galgame' },
];

const orderingOptions = [
  { label: 'Recently updated', value: '-updated_at' },
  { label: 'Recently added', value: '-created_at' },
  { label: 'Rating high to low', value: '-simple_rating' },
  { label: 'Rating low to high', value: 'simple_rating' },
];

function statusLabel(status: string) {
  return statusOptions.find((option) => option.value === status)?.label ?? status.replaceAll('_', ' ');
}

function buildPaginationItems(currentPage: number, totalPages: number): PaginationItem[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const pages = new Set([1, totalPages, currentPage, currentPage - 1, currentPage + 1]);
  if (currentPage <= 4) [2, 3, 4, 5].forEach((page) => pages.add(page));
  if (currentPage >= totalPages - 3) [totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1].forEach((page) => pages.add(page));

  const sortedPages = [...pages].filter((page) => page >= 1 && page <= totalPages).sort((a, b) => a - b);

  return sortedPages.flatMap((page, index) => {
    const previousPage = sortedPages[index - 1];
    if (!previousPage) return [page];
    if (page - previousPage === 2) return [previousPage + 1, page];
    if (page - previousPage > 2) return ['ellipsis' as const, page];
    return [page];
  });
}

export function LibraryPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const keyword = searchParams.get('keyword') ?? '';
  const status = (searchParams.get('status') ?? '') as UserSubjectStatus | '';
  const subjectType = (searchParams.get('subject_type') ?? '') as PrimarySubjectType | '';
  const tagId = searchParams.get('tag_id') ?? '';
  const ordering = searchParams.get('ordering') ?? '-updated_at';
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
  const [draftKeyword, setDraftKeyword] = useState(keyword);
  const [newTagName, setNewTagName] = useState('');
  const queryClient = useQueryClient();

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
  const createTagMutation = useMutation({
    mutationFn: (name: string) => tagsApi.createOrReuse({ name }),
    onSuccess: async () => {
      setNewTagName('');
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.tags() });
    },
  });
  const deleteTagMutation = useMutation({
    mutationFn: (id: number) => tagsApi.delete(id),
    onSuccess: async () => {
      updateSearchParam('tag_id', '');
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.tags() });
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.userSubjects() });
    },
  });
  const totalCount = libraryQuery.data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const paginationItems = useMemo(() => buildPaginationItems(currentPage, totalPages), [currentPage, totalPages]);

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.set('page', String(totalPages));
        return nextParams;
      });
    }
  }, [currentPage, setSearchParams, totalPages]);

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

  function handleCreateTag(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newTagName.trim();
    if (name) {
      createTagMutation.mutate(name);
    }
  }

  function goToPage(page: number) {
    updateSearchParam('page', String(Math.min(Math.max(page, 1), totalPages)));
  }

  return (
    <Page title="Library" eyebrow="Marked" description="Subjects you have marked with status, rating, progress, and notes.">
      <form className="grid gap-3 rounded-2xl bg-neutral-100 p-3 dark:bg-neutral-900/80" onSubmit={handleSubmit}>
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
          <Input value={draftKeyword} placeholder="Search your library" onChange={(event) => setDraftKeyword(event.target.value)} />
          <Button type="submit">Search</Button>
        </div>
        <div className="grid gap-2 md:grid-cols-4">
          <FilterMenu
            label="Status"
            options={statusOptions}
            value={status}
            onChange={(value) => updateSearchParam('status', value)}
          />
          <FilterMenu
            label="Type"
            options={typeOptions}
            value={subjectType}
            onChange={(value) => updateSearchParam('subject_type', value)}
          />
          <FilterMenu
            label="Tag"
            options={[
              { label: 'All tags', value: '' },
              ...(tagsQuery.data?.results ?? []).map((tag) => ({ label: tag.name, value: String(tag.id) })),
            ]}
            value={tagId}
            onChange={(value) => updateSearchParam('tag_id', value)}
          />
          <FilterMenu
            label="Sort"
            options={orderingOptions}
            value={ordering}
            onChange={(value) => updateSearchParam('ordering', value === '-updated_at' ? '' : value)}
          />
        </div>
      </form>

      <section className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm dark:border-neutral-800 dark:bg-neutral-950">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-base font-semibold tracking-tight text-neutral-950 dark:text-white">Tags</h2>
            <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">Filter and manage your personal library tags here.</p>
          </div>
          <form className="flex gap-2" onSubmit={handleCreateTag}>
            <Input className="h-10" value={newTagName} placeholder="New tag" onChange={(event) => setNewTagName(event.target.value)} />
            <Button disabled={createTagMutation.isPending} type="submit" variant="secondary">
              Add
            </Button>
          </form>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {(tagsQuery.data?.results ?? []).map((tag) => (
            <span className="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1.5 text-sm font-semibold text-neutral-700 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-300" key={tag.id}>
              <button className="transition hover:text-[var(--color-accent-strong)]" type="button" onClick={() => updateSearchParam('tag_id', String(tag.id))}>
                {tag.name}
              </button>
              <button className="text-neutral-400 transition hover:text-red-500" disabled={deleteTagMutation.isPending} type="button" aria-label={`Delete ${tag.name}`} onClick={() => deleteTagMutation.mutate(tag.id)}>
                <X className="size-3.5" />
              </button>
            </span>
          ))}
          {!tagsQuery.isLoading && (tagsQuery.data?.results.length ?? 0) === 0 ? (
            <span className="text-sm text-neutral-500 dark:text-neutral-400">No tags yet.</span>
          ) : null}
        </div>
      </section>

      <div className="flex items-center justify-between gap-3 text-sm text-neutral-500 dark:text-neutral-400">
        <span>{totalCount} subjects</span>
        {libraryQuery.isFetching ? <span>Loading</span> : null}
      </div>

      {libraryQuery.isLoading ? <LoadingState title="Loading library" /> : null}
      {libraryQuery.isError ? <ErrorState title="Unable to load library." description="Please try again later." /> : null}
      {!libraryQuery.isLoading && !libraryQuery.isError && libraryQuery.data?.results.length === 0 ? (
        <EmptyState title="No marked subjects yet." description="Open a subject page and add it to your library." />
      ) : null}

      <div className="grid gap-3">
        {(libraryQuery.data?.results ?? []).map((item) => (
          <Link
            className="grid min-w-0 grid-cols-[56px_minmax(0,1fr)_auto] gap-4 rounded-xl border border-neutral-200 bg-white p-3 shadow-sm transition hover:border-[var(--color-accent-border)] dark:border-neutral-800 dark:bg-neutral-950 max-sm:grid-cols-[52px_minmax(0,1fr)]"
            key={item.id}
            to={routes.subject(item.subject.id)}
          >
            <img
              className="h-20 w-14 rounded-lg bg-neutral-100 object-cover dark:bg-neutral-900 max-sm:h-[74px] max-sm:w-[52px]"
              src={item.subject.image_thumbnail || item.subject.image || coverPlaceholder}
              alt=""
              loading="lazy"
            />
            <span className="grid min-w-0 content-center gap-1">
              <span className="line-clamp-1 font-semibold text-neutral-950 dark:text-white">
                {item.subject.display_title || item.subject.title}
              </span>
              <span className="text-sm text-neutral-500 dark:text-neutral-400">{item.subject.display_subtitle || item.subject.subject_type}</span>
              {item.comment ? <span className="line-clamp-1 text-sm text-neutral-500 dark:text-neutral-400">{item.comment}</span> : null}
            </span>
            <span className="grid justify-items-end gap-2 self-center max-sm:col-start-2 max-sm:justify-items-start">
              <span className="rounded-full bg-neutral-100 px-3 py-1 text-sm font-semibold text-neutral-600 dark:bg-neutral-900 dark:text-neutral-300">
                {statusLabel(item.status)}
              </span>
              {item.simple_rating ? <span className="text-sm font-semibold text-neutral-500 dark:text-neutral-400">{item.simple_rating}/10</span> : null}
            </span>
          </Link>
        ))}
      </div>

      {totalPages > 1 ? (
        <div className="flex flex-wrap items-center gap-2 border-t border-neutral-200 pt-5 dark:border-neutral-800">
          <Button disabled={currentPage <= 1} type="button" variant="secondary" onClick={() => goToPage(currentPage - 1)}>
            Previous
          </Button>
          {paginationItems.map((item, index) =>
            item === 'ellipsis' ? (
              <span className="px-2 text-sm text-neutral-400" key={`ellipsis-${index}`}>
                ...
              </span>
            ) : (
              <Button
                className="min-w-10 px-3"
                key={item}
                size="sm"
                type="button"
                variant={item === currentPage ? 'default' : 'secondary'}
                onClick={() => goToPage(item)}
              >
                {item}
              </Button>
            ),
          )}
          <Button disabled={currentPage >= totalPages} type="button" variant="secondary" onClick={() => goToPage(currentPage + 1)}>
            Next
          </Button>
        </div>
      ) : null}
    </Page>
  );
}
