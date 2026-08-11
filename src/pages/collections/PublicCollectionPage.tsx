import { formatDate } from '@/shared/lib/date';
import { getRouteApi, Link, useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { CommunityCommentsSection } from '@/features/community';
import { CommunityTargetActions } from '@/features/community';
import { useI18n } from '@/shared/i18n';
import { PublicCollectionItemCard, PublicRatingStars } from '@/widgets/public-content';
import { publicUserQueries } from '@/entities/user';
import { routes } from '@/shared/routing/paths';
import { resolvedRouteHref } from '@/shared/routing/resolved-href';
import { parseIntegerParam } from '@/shared/routing/search-params';
import { backTargetFromState } from '@/shared/routing/route-state';
import { Badge } from '@/shared/ui/Badge';
import { Avatar } from '@/shared/ui/Avatar';
import { Button } from '@/shared/ui/Button';
import { DetailFooter, DetailHeader, DetailSection } from '@/shared/ui/Detail';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 24;
const publicCollectionRoute = getRouteApi('/users/$userId/collections/$collectionId');

function numberMeta(value: unknown) {
  return typeof value === 'number' ? value : undefined;
}

export function PublicCollectionPage() {
  const { t } = useI18n();
  const location = useLocation();
  const params = publicCollectionRoute.useParams();
  const navigate = publicCollectionRoute.useNavigate();
  const { collection_comments_page: commentsPage = 1, page: currentPage = 1 } = publicCollectionRoute.useSearch();
  const userId = parseIntegerParam(params.userId, { min: 1 }) ?? 0;
  const collectionId = parseIntegerParam(params.collectionId, { min: 1 }) ?? 0;
  const isValid = userId > 0 && collectionId > 0;
  const profileQuery = useQuery({ ...publicUserQueries.publicProfile(userId), enabled: isValid });
  const collectionQuery = useQuery({ ...publicUserQueries.publicCollection(userId, collectionId), enabled: isValid });
  const itemsQuery = useQuery({
    ...publicUserQueries.publicCollectionItems(userId, collectionId, { page: currentPage, page_size: pageSize }),
    enabled: isValid,
  });
  const items = itemsQuery.data?.results ?? [];
  const totalPages = Math.max(1, Math.ceil((itemsQuery.data?.count ?? 0) / pageSize));
  const backTarget = backTargetFromState(
    location,
    Number.isFinite(userId) && userId > 0 ? routes.userCollections(userId) : routes.home,
  );

  function goToPage(page: number) {
    void navigate({ search: (current) => ({ ...current, page }) });
  }

  if (!isValid) {
    return (
      <Page title={t('profile.collectionTitle')} eyebrow={t('profile.publicCollections')}>
        <ErrorState title={t('profile.invalidTitle')} description={t('profile.invalidBody')} />
      </Page>
    );
  }

  if (collectionQuery.isLoading) {
    return (
      <Page title={t('profile.collectionTitle')} eyebrow={t('profile.publicCollections')}>
        <LoadingState title={t('profile.loadingContent')} />
      </Page>
    );
  }

  if (collectionQuery.isError || !collectionQuery.data) {
    return (
      <Page title={t('profile.collectionTitle')} eyebrow={t('profile.publicCollections')}>
        <ErrorState title={t('profile.collectionErrorTitle')} description={t('profile.contentErrorBody')} />
      </Page>
    );
  }

  const collection = collectionQuery.data;
  const collectionTitleId = `collection-title-${collection.id}`;
  const collectionItemsTitleId = `collection-items-title-${collection.id}`;
  const collectionDate = collection.updated_at || collection.created_at;
  const itemCount = itemsQuery.data?.count ?? collection.item_count ?? 0;
  const itemsStatus = itemsQuery.isLoading
    ? 'loading'
    : itemsQuery.isError
      ? 'error'
      : items.length === 0
        ? 'empty'
        : 'ready';

  return (
    <Page
      seoDescription={collection.note || undefined}
      title={collection.name}
      eyebrow={t('profile.publicCollections')}
      headerMode="context"
      leading={
        <Button asChild aria-label={t('common.back')} size="icon-sm" tooltip={t('common.back')} variant="ghost">
          <Link {...resolvedRouteHref(backTarget)}>
            <ArrowLeft className="size-4" />
          </Link>
        </Button>
      }
      width="default"
    >
      <article aria-labelledby={collectionTitleId} className="mx-auto grid w-full max-w-6xl min-w-0 gap-6">
        <DetailHeader
          badges={
            <>
              <Badge variant="accent">{t('common.public')}</Badge>
              <Badge variant="secondary">
                {itemCount} {t('common.items')}
              </Badge>
              <PublicRatingStars
                emptyLabel={t('common.unrated')}
                ratingLabel={t('library.simpleRatingLabel')}
                value={collection.simple_rating}
              />
            </>
          }
          description={collection.note || t('profile.publicCollections')}
          meta={
            <>
              <Avatar alt={profileQuery.data?.nickname || t('common.anonymous')} src={profileQuery.data?.avatar} />
              <div className="min-w-0">
                {profileQuery.data ? (
                  <Link
                    className="block truncate text-sm font-semibold text-foreground hover:text-[var(--ui-accent-text)]"
                    to={routes.userProfile(profileQuery.data.id)}
                  >
                    {profileQuery.data.nickname || t('common.anonymous')}
                  </Link>
                ) : (
                  <p className="truncate text-sm font-semibold text-foreground">{t('common.anonymous')}</p>
                )}
                <time className="block text-xs text-muted-foreground" dateTime={collectionDate}>
                  {formatDate(collectionDate)}
                </time>
              </div>
            </>
          }
          title={collection.name}
          titleId={collectionTitleId}
        />

        <DetailSection
          meta={`${itemCount} ${t('common.items')}`}
          title={t('collections.itemsTitle')}
          titleId={collectionItemsTitleId}
        >
          {itemsStatus === 'loading' ? <LoadingState title={t('profile.loadingCollectionItems')} /> : null}
          {itemsStatus === 'error' ? (
            <ErrorState title={t('profile.collectionItemsErrorTitle')} description={t('profile.contentErrorBody')} />
          ) : null}
          {itemsStatus === 'empty' ? (
            <EmptyState title={t('profile.noCollectionItemsTitle')} description={t('profile.noCollectionItemsBody')} />
          ) : null}
          {itemsStatus === 'ready' ? (
            <ul className="m-0 grid list-none gap-x-4 gap-y-6 p-0 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              {items.map((item) => (
                <li className="min-w-0" key={item.id}>
                  <PublicCollectionItemCard item={item} />
                </li>
              ))}
            </ul>
          ) : null}
          {itemsStatus === 'ready' ? (
            <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
          ) : null}
        </DetailSection>

        <DetailFooter>
          <CommunityTargetActions
            presentation="inline"
            reactionCount={numberMeta(collection.reaction_count)}
            reportLabel={t('community.reportCollection')}
            targetId={collection.id}
            targetType="collection"
            viewerState={collection.viewer_state}
          />
        </DetailFooter>
      </article>

      <div className="mx-auto mt-6 w-full max-w-6xl border-t border-border-subtle pt-6" data-slot="detail-comments">
        <CommunityCommentsSection
          currentPage={commentsPage}
          targetType="collection"
          targetId={collection.id}
          onPageChange={(page) =>
            void navigate({ search: (current) => ({ ...current, collection_comments_page: page }) })
          }
        />
      </div>
    </Page>
  );
}
