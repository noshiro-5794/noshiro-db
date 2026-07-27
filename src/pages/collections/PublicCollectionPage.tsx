import { Link, useLocation, useParams, useSearchParams } from '@/shared/routing/navigation';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { CommunityCommentsSection } from '@/features/community';
import { CommunityTargetActions } from '@/features/community';
import { useI18n } from '@/shared/i18n';
import { PublicCollectionRailItem, PublicRatingStars } from '@/widgets/public-content';
import { publicUserQueries } from '@/entities/user';
import { routes } from '@/shared/routing/paths';
import { backTargetFromState } from '@/shared/routing/route-state';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 24;

function numberMeta(value: unknown) {
  return typeof value === 'number' ? value : undefined;
}

export function PublicCollectionPage() {
  const { t } = useI18n();
  const location = useLocation();
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const userId = Number(params.userId);
  const collectionId = Number(params.collectionId);
  const isValid = Number.isFinite(userId) && userId > 0 && Number.isFinite(collectionId) && collectionId > 0;
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
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
    const next = new URLSearchParams(searchParams);
    next.set('page', String(page));
    setSearchParams(next);
  }

  if (!isValid) {
    return (
      <Page title={t('profile.collectionTitle')} eyebrow={t('profile.publicCollections')}>
        <ErrorState title={t('profile.invalidTitle')} description={t('profile.invalidBody')} />
      </Page>
    );
  }

  return (
    <Page
      title={collectionQuery.data?.name || t('profile.collectionTitle')}
      eyebrow={t('profile.publicCollections')}
      actions={
        <Button asChild type="button" variant="secondary">
          <Link to={backTarget}>
            <ArrowLeft className="size-4" /> {t('common.back')}
          </Link>
        </Button>
      }
    >
      {profileQuery.isLoading || collectionQuery.isLoading ? (
        <LoadingState title={t('profile.loadingContent')} />
      ) : null}
      {profileQuery.isError || collectionQuery.isError ? (
        <ErrorState title={t('profile.collectionErrorTitle')} description={t('profile.contentErrorBody')} />
      ) : null}
      {collectionQuery.data ? (
        <>
          <section className="content-reader">
            <header className="content-reader-header">
              <div className="content-reader-author">
                <img alt="" src={profileQuery.data?.avatar || '/assets/placeholders/avatar.png'} />
                <div className="min-w-0">
                  <p>{profileQuery.data?.nickname || t('common.anonymous')}</p>
                  <span>{t('profile.publicCollections')}</span>
                </div>
              </div>
              <div className="content-reader-badges">
                <Badge variant="accent">{t('common.public')}</Badge>
                <Badge variant="secondary">
                  {collectionQuery.data.item_count ?? itemsQuery.data?.count ?? 0} {t('common.items')}
                </Badge>
                <PublicRatingStars
                  emptyLabel={t('common.unrated')}
                  ratingLabel={t('library.simpleRatingLabel')}
                  value={collectionQuery.data.simple_rating}
                />
              </div>
            </header>
            {collectionQuery.data.note ? <p className="content-reader-note">{collectionQuery.data.note}</p> : null}
            <div className="content-reader-section-header">
              <h2>{t('collections.itemsTitle')}</h2>
              <span>
                {itemsQuery.data?.count ?? collectionQuery.data.item_count ?? 0} {t('common.items')}
              </span>
            </div>
            {itemsQuery.isLoading ? <LoadingState title={t('profile.loadingCollectionItems')} /> : null}
            {itemsQuery.isError ? (
              <ErrorState title={t('profile.collectionItemsErrorTitle')} description={t('profile.contentErrorBody')} />
            ) : null}
            {!itemsQuery.isLoading && !itemsQuery.isError && items.length === 0 ? (
              <EmptyState
                title={t('profile.noCollectionItemsTitle')}
                description={t('profile.noCollectionItemsBody')}
              />
            ) : null}
            <div className="collection-rail content-reader-rail" aria-label={t('collections.itemsTitle')}>
              {items.map((item) => (
                <PublicCollectionRailItem item={item} key={item.id} />
              ))}
            </div>
            <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
            <footer className="content-reader-actions">
              <CommunityTargetActions
                presentation="inline"
                reactionCount={numberMeta(collectionQuery.data.reaction_count)}
                reportLabel={t('community.reportCollection')}
                targetId={collectionQuery.data.id}
                targetType="collection"
                viewerState={collectionQuery.data.viewer_state}
              />
            </footer>
          </section>
          <section className="content-reader-section">
            <CommunityCommentsSection targetType="collection" targetId={collectionQuery.data.id} />
          </section>
        </>
      ) : null}
    </Page>
  );
}
