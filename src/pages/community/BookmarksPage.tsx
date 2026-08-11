import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { formatDate } from '@/shared/lib/date';
import { type SyntheticEvent, useEffect, useState } from 'react';
import { getRouteApi, Link, useLocation } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bookmark, ExternalLink, FileText, Layers3, MessageSquare, Star, Trash2 } from 'lucide-react';
import { invalidateCommunityTargets } from '@/features/community';
import { communityMutations, communityQueries } from '@/entities/community';
import { useI18n } from '@/shared/i18n';
import { useVisibleOnce } from '@/shared/lib/use-visible-once';
import { publicUserQueries } from '@/entities/user';
import type { CommunityBookmark } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { resolvedRouteHref } from '@/shared/routing/resolved-href';
import { validateBookmarksSearch } from '@/shared/routing/route-search';
import type { RouteBackState } from '@/shared/routing/route-state';
import { routeBackState } from '@/shared/routing/route-state';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import {
  ContentRow,
  ContentRowActions,
  ContentRowAuthor,
  ContentRowExcerpt,
  ContentRowFooter,
  ContentRowHeading,
  ContentRowMain,
  ContentRowMedia,
  ContentRowMeta,
  ContentRowReference,
  ContentRowTitle,
} from '@/shared/ui/ContentRow';
import {
  DataToolbar,
  DataToolbarPrimary,
  DataToolbarRow,
  ListSurface,
  ResultsMeta,
  ResultsState,
  SearchField,
  type ResultsStatus,
} from '@/shared/ui/DataView';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';
import { SpoilerText } from '@/shared/ui/SpoilerText';
import { toast } from '@/shared/ui/toast';

const pageSize = 18;
const targetFilters = ['', 'post', 'review', 'collection'] as const;
type BookmarkFilter = (typeof targetFilters)[number];
const bookmarksRoute = getRouteApi('/bookmarks');

function bookmarkHref(bookmark: CommunityBookmark) {
  if (bookmark.target_type === 'post') return routes.communityPost(bookmark.target_id);
  if (bookmark.target_type === 'review') return routes.review(bookmark.target_id);
  if (bookmark.target_type === 'collection' && bookmark.target?.author?.id)
    return routes.userCollection(bookmark.target.author.id, bookmark.target_id);
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
  const { isVisible, ref } = useVisibleOnce();
  const previewQuery = useQuery({
    ...publicUserQueries.publicCollectionItems(userId, collectionId, { page: 1, page_size: 1 }),
    enabled: isVisible && Boolean(userId && collectionId),
  });
  const cover = previewQuery.data?.results[0]?.subject.image_thumbnail;

  if (cover) return <img alt="" decoding="async" loading="lazy" referrerPolicy="no-referrer" src={cover} />;
  return (
    <span ref={ref}>
      <Layers3 className="size-4" />
    </span>
  );
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
    <ContentRow>
      <ContentRowMedia>
        <Link
          aria-label={subject ? subjectTitle : title}
          state={state}
          {...resolvedRouteHref(subject ? routes.subject(subject.id) : href)}
        >
          {canShowCollectionCover && author?.id ? (
            <BookmarkCollectionCover collectionId={bookmark.target_id} userId={author.id} />
          ) : cover ? (
            <img alt="" decoding="async" loading="lazy" referrerPolicy="no-referrer" src={cover} />
          ) : (
            <span>
              <BookmarkIcon type={bookmark.target_type} />
            </span>
          )}
        </Link>
      </ContentRowMedia>

      <ContentRowMain>
        <ContentRowMeta>
          <Badge variant="secondary">{typeLabel}</Badge>
          <span>{formatDate(bookmark.created_at)}</span>
          {!bookmark.target ? <Badge>{t('community.bookmarkDetailUnavailable')}</Badge> : null}
          {bookmark.target?.is_spoiler ? <Badge>{t('common.spoiler')}</Badge> : null}
          {bookmark.target?.simple_rating ? (
            <span className="inline-flex items-center gap-0.5 text-[var(--ui-accent-text)]">
              {Array.from({ length: 5 }, (_, index) => (
                <Star
                  className={`size-3 ${
                    index < Number(bookmark.target?.simple_rating)
                      ? 'fill-current'
                      : 'text-[color-mix(in_srgb,var(--ui-text-muted)_34%,transparent)]'
                  }`}
                  key={index}
                />
              ))}
            </span>
          ) : null}
        </ContentRowMeta>

        <ContentRowHeading>
          <ContentRowTitle>
            <Link state={state} {...resolvedRouteHref(href)}>
              {title}
            </Link>
          </ContentRowTitle>
          <ContentRowActions>
            <Button
              asChild
              aria-label={t('community.openTarget')}
              size="icon"
              tooltip={t('community.openTarget')}
              type="button"
              variant="ghost"
            >
              <Link state={state} {...resolvedRouteHref(href)}>
                <ExternalLink className="size-4" />
              </Link>
            </Button>
            <Button
              aria-label={t('community.removeBookmark')}
              disabled={isRemoving}
              size="icon"
              tooltip={t('community.removeBookmark')}
              type="button"
              variant="ghost"
              onClick={() => {
                onRemove(bookmark);
              }}
            >
              <Trash2 className="size-4" />
            </Button>
          </ContentRowActions>
        </ContentRowHeading>
        {body ? (
          <ContentRowExcerpt>
            <SpoilerText isSpoiler={Boolean(bookmark.target?.is_spoiler)} revealLabel={t('common.revealSpoiler')}>
              {body}
            </SpoilerText>
          </ContentRowExcerpt>
        ) : null}

        {subject ? (
          <ContentRowReference>
            <Link params={{ subjectId: subject.id }} state={state} to="/subjects/$subjectId">
              <span>{subjectTitle}</span>
              {subject.subject_type ? <small>{subject.subject_type}</small> : null}
            </Link>
          </ContentRowReference>
        ) : null}

        {author?.id ? (
          <ContentRowFooter>
            <ContentRowAuthor>
              <Link params={{ userId: String(author.id) }} to="/users/$userId">
                <img
                  alt=""
                  decoding="async"
                  loading="lazy"
                  referrerPolicy="no-referrer"
                  src={author.avatar || placeholderImagePaths.avatar}
                />
                <span>{author.nickname || t('common.anonymous')}</span>
              </Link>
            </ContentRowAuthor>
          </ContentRowFooter>
        ) : null}
      </ContentRowMain>
    </ContentRow>
  );
}

export function BookmarksPage() {
  const { t } = useI18n();
  const location = useLocation();
  const queryClient = useQueryClient();
  const navigate = bookmarksRoute.useNavigate();
  const search = bookmarksRoute.useSearch();
  const currentPage = search.page ?? 1;
  const routeState = routeBackState(location, t('nav.bookmarks'));
  const keyword = search.keyword ?? '';
  const targetType = search.target_type ?? '';
  const [draftKeyword, setDraftKeyword] = useState(keyword);
  const normalizedTargetType = targetType;
  const targetTypeOptions: Array<{ label: string; value: BookmarkFilter }> = targetFilters.map((filter) => ({
    label: filter ? targetTypeLabel(t, filter) : t('common.all'),
    value: filter,
  }));
  const bookmarksQuery = useQuery(
    communityQueries.bookmarks({
      page: currentPage,
      page_size: pageSize,
      ...(normalizedTargetType ? { target_type: normalizedTargetType } : {}),
      ...(keyword ? { keyword } : {}),
    }),
  );
  const removeBookmarkMutation = useMutation({
    ...communityMutations.unbookmark(),
    onError: () => toast.error(t('common.requestFailed')),
    onSuccess: async () => {
      await invalidateCommunityTargets(queryClient);
    },
  });
  const bookmarks = bookmarksQuery.data?.results ?? [];
  const totalPages = Math.max(1, Math.ceil((bookmarksQuery.data?.count ?? 0) / pageSize));
  const resultsStatus: ResultsStatus =
    bookmarksQuery.data === undefined && bookmarksQuery.isLoading
      ? 'loading'
      : bookmarksQuery.data === undefined && bookmarksQuery.isError
        ? 'error'
        : bookmarks.length === 0
          ? 'empty'
          : 'ready';

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  useEffect(() => {
    if (bookmarksQuery.data && currentPage > totalPages) {
      void navigate({ replace: true, search: (current) => ({ ...current, page: totalPages }) });
    }
  }, [bookmarksQuery.data, currentPage, navigate, totalPages]);

  function updateParams(nextParams: { page?: number; target_type?: BookmarkFilter; keyword?: string }) {
    const resetsPage = nextParams.target_type !== undefined || nextParams.keyword !== undefined;
    void navigate({
      search: (current) => ({
        ...current,
        ...validateBookmarksSearch({
          ...current,
          ...nextParams,
          page: resetsPage ? undefined : nextParams.page,
        }),
      }),
    });
  }

  function handleSearch(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
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
        <DataToolbar onSubmit={handleSearch}>
          <DataToolbarRow className="lg:grid-cols-[minmax(0,1fr)_190px_auto]">
            <DataToolbarPrimary>
              <SearchField
                aria-label={t('community.bookmarksSearchPlaceholder')}
                maxLength={200}
                value={draftKeyword}
                placeholder={t('community.bookmarksSearchPlaceholder')}
                onChange={(event) => {
                  setDraftKeyword(event.target.value);
                }}
              />
            </DataToolbarPrimary>
            <FilterMenu
              label={t('search.type')}
              options={targetTypeOptions}
              size="lg"
              value={normalizedTargetType}
              onChange={(value) => {
                updateParams({ target_type: value });
              }}
            />
            <Button size="lg" type="submit" variant="secondary">
              {t('common.search')}
            </Button>
          </DataToolbarRow>
        </DataToolbar>

        <ResultsMeta
          count={bookmarksQuery.data?.count}
          label={t('nav.bookmarks')}
          pending={bookmarksQuery.isFetching && !bookmarksQuery.isLoading}
          pendingLabel={t('common.loading')}
        />

        <ResultsState
          emptyAction={
            <Button asChild size="sm" type="button" variant="secondary">
              <Link to={routes.communityPosts}>{t('nav.posts')}</Link>
            </Button>
          }
          emptyDescription={t('community.noBookmarksBody')}
          emptyTitle={t('community.noBookmarksTitle')}
          errorDescription={t('community.bookmarksErrorBody')}
          errorTitle={t('community.bookmarksErrorTitle')}
          loadingTitle={t('community.loadingBookmarks')}
          status={resultsStatus}
        >
          <>
            <ListSurface>
              {bookmarks.map((bookmark) => (
                <BookmarkCard
                  bookmark={bookmark}
                  isRemoving={removeBookmarkMutation.isPending}
                  key={bookmark.id}
                  state={routeState}
                  onRemove={removeBookmark}
                />
              ))}
            </ListSurface>
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={(page) => {
                updateParams({ page });
              }}
            />
          </>
        </ResultsState>
      </div>
    </Page>
  );
}
