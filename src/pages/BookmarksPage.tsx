import { type FormEvent, useEffect, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bookmark, ExternalLink, FileText, Layers3, MessageSquare, Search, Star, Trash2 } from 'lucide-react';
import { invalidateCommunityTargets } from '@/features/community/cache';
import { communityMutations, communityQueries, communityQueryKeys } from '@/features/community/community-queries';
import { useI18n } from '@/features/i18n/use-i18n';
import { socialQueries } from '@/features/social/social-queries';
import type { CommunityBookmark } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import type { RouteBackState } from '@/shared/navigation/route-state';
import { routeBackState } from '@/shared/navigation/route-state';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
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

function BookmarkCollectionCover({ collectionId, userId }: { collectionId: number; userId: number }) {
  const previewQuery = useQuery({
    ...socialQueries.publicCollectionItems(userId, collectionId, { page: 1, page_size: 1 }),
    enabled: Boolean(userId && collectionId),
  });
  const cover = previewQuery.data?.results?.[0]?.subject?.image_thumbnail;

  if (cover) return <img src={cover} alt="" loading="lazy" />;
  return <span><Layers3 className="size-4" /></span>;
}

function BookmarkCard({
  bookmark,
  isRemoving,
  onRemove,
  state,
}: {
  bookmark: CommunityBookmark;
  isRemoving: boolean;
  onRemove: (bookmark: CommunityBookmark) => void;
  state: RouteBackState;
}) {
  const { t } = useI18n();
  const href = bookmarkHref(bookmark);
  const title = bookmark.target?.title || `${bookmark.target_type} #${bookmark.target_id}`;
  const body = bookmark.target?.body || '';
  const author = bookmark.target?.author;
  const subject = bookmark.target?.subject;
  const cover = bookmark.target_type === 'collection' ? null : subject?.image_thumbnail;
  const subjectTitle = subject?.title || subject?.title_cn || t('common.untitledSubject');
  const typeLabel = targetTypeLabel(t, bookmark.target_type);
  const canShowCollectionCover = bookmark.target_type === 'collection' && Boolean(author?.id);

  return (
    <article className="bookmark-card">
      <Link className="bookmark-card-visual" state={state} to={subject ? routes.subject(subject.id) : href}>
        {canShowCollectionCover && author?.id ? (
          <BookmarkCollectionCover collectionId={bookmark.target_id} userId={author.id} />
        ) : cover ? (
          <img src={cover} alt="" loading="lazy" />
        ) : (
          <span><BookmarkIcon type={bookmark.target_type} /></span>
        )}
      </Link>

      <div className="bookmark-card-main">
        <div className="bookmark-card-meta">
          <Badge variant="secondary">{typeLabel}</Badge>
          <span>{formatDate(bookmark.created_at)}</span>
          {!bookmark.target ? <Badge>{t('community.bookmarkDetailUnavailable')}</Badge> : null}
          {bookmark.target?.is_spoiler ? <Badge>{t('common.spoiler')}</Badge> : null}
          {bookmark.target?.simple_rating ? (
            <span className="bookmark-card-stars">
              {Array.from({ length: 5 }, (_, index) => (
                <Star className={`size-3 ${index < Number(bookmark.target?.simple_rating) ? 'fill-current' : ''}`} key={index} />
              ))}
            </span>
          ) : null}
        </div>

        <div className="bookmark-card-heading">
          <Link className="bookmark-card-title" state={state} to={href}>{title}</Link>
          <div className="bookmark-card-actions">
            <Button asChild size="icon" type="button" variant="ghost" aria-label={t('community.openTarget')}>
              <Link state={state} to={href}><ExternalLink className="size-4" /></Link>
            </Button>
            <Button aria-label={t('community.removeBookmark')} disabled={isRemoving} size="icon" type="button" variant="ghost" onClick={() => onRemove(bookmark)}>
              <Trash2 className="size-4" />
            </Button>
          </div>
        </div>
        {body ? <p className={`bookmark-card-body ${bookmark.target?.is_spoiler ? 'is-spoiler' : ''}`}>{body}</p> : null}

        {subject ? (
          <Link className="bookmark-card-subject" state={state} to={routes.subject(subject.id)}>
            <span>{subjectTitle}</span>
            {subject.subject_type ? <small>{subject.subject_type}</small> : null}
          </Link>
        ) : null}

        <div className="bookmark-card-footer">
          {author?.id ? (
            <Link className="bookmark-card-author" to={routes.userProfile(author.id)}>
              <img src={author.avatar || '/assets/placeholders/avatar.png'} alt="" />
              <span>{author.nickname || t('common.anonymous')}</span>
            </Link>
          ) : <span />}
        </div>
      </div>
    </article>
  );
}

export function BookmarksPage() {
  const { t } = useI18n();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
  const routeState = routeBackState(location, t('nav.bookmarks'));
  const keyword = searchParams.get('keyword') ?? '';
  const targetType = (searchParams.get('target_type') ?? '') as BookmarkFilter;
  const [draftKeyword, setDraftKeyword] = useState(keyword);
  const normalizedTargetType = targetFilters.includes(targetType) ? targetType : '';
  const targetTypeOptions: Array<{ label: string; value: BookmarkFilter }> = targetFilters.map((filter) => ({
    label: filter ? targetTypeLabel(t, filter) : t('common.all'),
    value: filter,
  }));
  const bookmarksQuery = useQuery(communityQueries.bookmarks({
    page: currentPage,
    page_size: pageSize,
    target_type: normalizedTargetType || undefined,
    keyword: keyword || undefined,
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

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  useEffect(() => {
    if (bookmarksQuery.data && currentPage > totalPages) {
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.set('page', String(totalPages));
        return nextParams;
      });
    }
  }, [bookmarksQuery.data, currentPage, setSearchParams, totalPages]);

  function updateParams(nextParams: { page?: number; target_type?: BookmarkFilter; keyword?: string }) {
    const next = new URLSearchParams(searchParams);
    if (nextParams.page) next.set('page', String(nextParams.page));
    if (nextParams.target_type !== undefined) {
      if (nextParams.target_type) next.set('target_type', nextParams.target_type);
      else next.delete('target_type');
      next.set('page', '1');
    }
    if (nextParams.keyword !== undefined) {
      if (nextParams.keyword) next.set('keyword', nextParams.keyword);
      else next.delete('keyword');
      next.set('page', '1');
    }
    setSearchParams(next);
  }

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateParams({ keyword: draftKeyword.trim() });
  }

  function removeBookmark(bookmark: CommunityBookmark) {
    removeBookmarkMutation.mutate({
      target_type: bookmark.target_type,
      target_id: bookmark.target_id,
    });
  }

  return (
    <Page title={t('community.bookmarksTitle')} eyebrow={t('nav.groupLibrary')}>
      <div className="grid gap-5">
        <form className="content-toolbar" onSubmit={handleSearch}>
          <div className="content-toolbar-grid is-bookmark">
            <div className="content-toolbar-search">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-400" />
              <Input
                className="pl-9"
                value={draftKeyword}
                placeholder={t('community.bookmarksSearchPlaceholder')}
                onChange={(event) => setDraftKeyword(event.target.value)}
              />
            </div>
            <FilterMenu label={t('search.type')} options={targetTypeOptions} value={normalizedTargetType} onChange={(value) => updateParams({ target_type: value })} />
            <Button type="submit" variant="secondary">{t('common.search')}</Button>
          </div>
        </form>

        <div className="content-summary-bar">
          <div className="content-summary-count">
            <span className="content-summary-number">{bookmarksQuery.data?.count ?? 0}</span>
            <span>{t('nav.bookmarks')}</span>
          </div>
          <div className="content-summary-side">
            {bookmarksQuery.isFetching ? <span>{t('common.loading')}</span> : null}
            <span className="content-summary-page">{t('common.page')} {currentPage} / {totalPages}</span>
          </div>
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
              state={routeState}
              onRemove={removeBookmark}
            />
          ))}
        </div>
        <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={(page) => updateParams({ page })} />
      </div>
    </Page>
  );
}
