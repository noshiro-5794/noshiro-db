import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bookmark, FileText, Layers3, MessageSquare, Star, Trash2 } from 'lucide-react';
import { invalidateCommunityTargets } from '@/features/community/cache';
import { CommunityContentCard } from '@/features/community/components/CommunityContentCard';
import { communityMutations, communityQueries, communityQueryKeys } from '@/features/community/community-queries';
import { useI18n } from '@/features/i18n/use-i18n';
import type { CommunityBookmark } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 18;
const targetFilters = ['', 'post', 'review', 'collection'] as const;
type BookmarkFilter = (typeof targetFilters)[number];

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function bookmarkHref(bookmark: CommunityBookmark) {
  if (bookmark.target_type === 'post') return routes.communityPost(bookmark.target_id);
  if (bookmark.target_type === 'review') return routes.review(bookmark.target_id);
  if (bookmark.target_type === 'collection' && bookmark.target?.author?.id) return routes.userCollection(bookmark.target.author.id, bookmark.target_id);
  if (bookmark.target_type === 'collection') return routes.collections;
  return routes.bookmarks;
}

function BookmarkIcon({ type }: { type: string }) {
  if (type === 'post') return <MessageSquare className="size-4" />;
  if (type === 'review') return <FileText className="size-4" />;
  if (type === 'collection') return <Layers3 className="size-4" />;
  return <Bookmark className="size-4" />;
}

function targetTypeLabel(t: ReturnType<typeof useI18n>['t'], type: string) {
  if (type === 'post') return t('community.targetType.post');
  if (type === 'review') return t('community.targetType.review');
  if (type === 'collection') return t('community.targetType.collection');
  return type;
}

function BookmarkCard({
  bookmark,
  isRemoving,
  onRemove,
}: {
  bookmark: CommunityBookmark;
  isRemoving: boolean;
  onRemove: (bookmark: CommunityBookmark) => void;
}) {
  const { t } = useI18n();
  const href = bookmarkHref(bookmark);
  const title = bookmark.target?.title || `${bookmark.target_type} #${bookmark.target_id}`;
  const body = bookmark.target?.body || bookmark.target?.subject?.title || bookmark.target?.subject?.title_cn || '';
  const author = bookmark.target?.author;

  return (
    <CommunityContentCard
      actions={(
        <>
          <Button asChild size="sm" type="button" variant="secondary">
            <Link to={href}>{t('community.openTarget')}</Link>
          </Button>
          <Button disabled={isRemoving} size="sm" type="button" variant="ghost" onClick={() => onRemove(bookmark)}>
            <Trash2 className="size-4" /> {t('community.removeBookmark')}
          </Button>
        </>
      )}
      author={author?.id ? {
        href: routes.userProfile(author.id),
        name: author.nickname || t('common.anonymous'),
        avatar: author.avatar,
      } : undefined}
      badges={(
        <>
          {!bookmark.target ? <Badge>{t('community.bookmarkDetailUnavailable')}</Badge> : null}
          {bookmark.target?.is_spoiler ? <Badge>{t('common.spoiler')}</Badge> : null}
          {bookmark.target?.simple_rating ? (
            <span className="inline-flex items-center gap-0.5 text-[var(--color-accent-strong)]">
              {Array.from({ length: 5 }, (_, index) => (
                <Star className={`size-3 ${index < Number(bookmark.target?.simple_rating) ? 'fill-current' : 'text-neutral-300 dark:text-neutral-700'}`} key={index} />
              ))}
            </span>
          ) : null}
        </>
      )}
      body={body}
      date={formatDate(bookmark.created_at)}
      href={href}
      icon={<BookmarkIcon type={bookmark.target_type} />}
      isSpoiler={bookmark.target?.is_spoiler}
      subject={bookmark.target?.subject ? {
        href: routes.subject(bookmark.target.subject.id),
        title: bookmark.target.subject.title || bookmark.target.subject.title_cn || t('common.untitledSubject'),
      } : undefined}
      title={title}
      typeLabel={targetTypeLabel(t, bookmark.target_type)}
    />
  );
}

export function BookmarksPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
  const targetType = (searchParams.get('target_type') ?? '') as BookmarkFilter;
  const normalizedTargetType = targetFilters.includes(targetType) ? targetType : '';
  const bookmarksQuery = useQuery(communityQueries.bookmarks({
    page: currentPage,
    page_size: pageSize,
    target_type: normalizedTargetType || undefined,
  }));
  const removeBookmarkMutation = useMutation({
    ...communityMutations.unbookmark(),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: communityQueryKeys.bookmarks() }),
        invalidateCommunityTargets(queryClient),
      ]);
    },
  });
  const bookmarks = bookmarksQuery.data?.results ?? [];
  const totalPages = Math.max(1, Math.ceil((bookmarksQuery.data?.count ?? 0) / pageSize));

  function updateParams(nextParams: { page?: number; target_type?: BookmarkFilter }) {
    const next = new URLSearchParams(searchParams);
    if (nextParams.page) next.set('page', String(nextParams.page));
    if (nextParams.target_type !== undefined) {
      if (nextParams.target_type) next.set('target_type', nextParams.target_type);
      else next.delete('target_type');
      next.set('page', '1');
    }
    setSearchParams(next);
  }

  function removeBookmark(bookmark: CommunityBookmark) {
    removeBookmarkMutation.mutate({
      target_type: bookmark.target_type,
      target_id: bookmark.target_id,
    });
  }

  return (
    <Page title={t('community.bookmarksTitle')} eyebrow={t('nav.groupWorkspace')} description={t('community.bookmarksDescription')}>
      <div className="flex flex-wrap gap-2">
        {targetFilters.map((filter) => (
          <button
            className={[
              'rounded-full border px-3 py-1.5 text-sm font-semibold transition',
              normalizedTargetType === filter
                ? 'border-[var(--color-accent-border)] bg-[var(--color-accent-soft)] text-[var(--color-accent-strong)]'
                : 'border-neutral-200 bg-white text-neutral-500 hover:border-neutral-300 hover:text-neutral-950 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-400 dark:hover:text-white',
            ].join(' ')}
            key={filter || 'all'}
            type="button"
            onClick={() => updateParams({ target_type: filter })}
          >
            {filter ? targetTypeLabel(t, filter) : t('common.all')}
          </button>
        ))}
      </div>

      <div className="grid gap-4">
        <div className="flex items-center justify-between gap-3 text-sm text-neutral-500 dark:text-neutral-400">
          <span>{bookmarksQuery.data?.count ?? 0} {t('nav.bookmarks')}</span>
          {bookmarksQuery.isFetching ? <span>{t('common.loading')}</span> : null}
        </div>

        {bookmarksQuery.isLoading ? <LoadingState title={t('community.loadingBookmarks')} /> : null}
        {bookmarksQuery.isError ? <ErrorState title={t('community.bookmarksErrorTitle')} description={t('community.bookmarksErrorBody')} /> : null}
        {!bookmarksQuery.isLoading && !bookmarksQuery.isError && bookmarks.length === 0 ? (
          <EmptyState
            title={t('community.noBookmarksTitle')}
            description={t('community.noBookmarksBody')}
            action={(
              <Button asChild size="sm" type="button" variant="secondary">
                <Link to={routes.communityPosts}>{t('nav.posts')}</Link>
              </Button>
            )}
          />
        ) : null}
        <div className="community-bookmark-list">
          {bookmarks.map((bookmark) => (
            <BookmarkCard
              bookmark={bookmark}
              isRemoving={removeBookmarkMutation.isPending}
              key={bookmark.id}
              onRemove={removeBookmark}
            />
          ))}
        </div>
        <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={(page) => updateParams({ page })} />
      </div>
    </Page>
  );
}
