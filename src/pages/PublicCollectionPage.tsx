import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Star } from 'lucide-react';
import { CommunityCommentsSection } from '@/features/community/components/CommunityCommentsSection';
import { CommunityTargetActions } from '@/features/community/components/CommunityTargetActions';
import { useI18n } from '@/features/i18n/use-i18n';
import { socialQueries } from '@/features/social/social-queries';
import type { CollectionItem } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 24;
const coverPlaceholder = '/assets/placeholders/subject-cover.png';

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function numberMeta(value: unknown) {
  return typeof value === 'number' ? value : undefined;
}

function subjectTitle(item: CollectionItem, fallback: string) {
  return item.subject.display_title || item.subject.title || item.subject.title_cn || fallback;
}

function StarRating({ value }: { value: number | null }) {
  if (!value) return null;

  return (
    <span className="inline-flex items-center gap-0.5 text-[var(--color-accent-strong)]">
      {Array.from({ length: 5 }, (_, index) => (
        <Star className={`size-3.5 ${index < value ? 'fill-current' : 'text-neutral-300 dark:text-neutral-700'}`} key={index} />
      ))}
    </span>
  );
}

function CollectionSubjectItem({ item }: { item: CollectionItem }) {
  const { t } = useI18n();

  return (
    <Link className="grid grid-cols-[58px_minmax(0,1fr)] gap-3 border-b border-neutral-200 p-3 transition last:border-b-0 hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900/60" to={routes.subject(item.subject.id)}>
      <img className="h-20 w-14 rounded-md bg-neutral-100 object-cover dark:bg-neutral-900" src={item.subject.image_thumbnail || item.subject.image || coverPlaceholder} alt="" />
      <span className="grid min-w-0 content-center">
        <span className="line-clamp-1 text-sm font-semibold text-neutral-950 dark:text-white">{subjectTitle(item, t('common.untitledSubject'))}</span>
        <span className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
          {item.subject.subject_type}
          {item.subject.date ? ` · ${formatDate(item.subject.date)}` : ''}
        </span>
        <span className="mt-2 flex flex-wrap items-center gap-2">
          {item.relation ? <Badge variant="secondary">{item.relation}</Badge> : null}
          <StarRating value={item.user_subject.simple_rating} />
        </span>
        {item.user_subject.comment ? (
          <span className="mt-2 line-clamp-2 text-sm leading-6 text-neutral-500 dark:text-neutral-400">{item.user_subject.comment}</span>
        ) : null}
      </span>
    </Link>
  );
}

export function PublicCollectionPage() {
  const { t } = useI18n();
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const userId = Number(params.userId);
  const collectionId = Number(params.collectionId);
  const isValid = Number.isFinite(userId) && userId > 0 && Number.isFinite(collectionId) && collectionId > 0;
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
  const profileQuery = useQuery({ ...socialQueries.publicProfile(userId), enabled: isValid });
  const collectionQuery = useQuery({ ...socialQueries.publicCollection(userId, collectionId), enabled: isValid });
  const itemsQuery = useQuery({
    ...socialQueries.publicCollectionItems(userId, collectionId, { page: currentPage, page_size: pageSize }),
    enabled: isValid,
  });
  const items = itemsQuery.data?.results ?? [];
  const totalPages = Math.max(1, Math.ceil((itemsQuery.data?.count ?? 0) / pageSize));

  function goToPage(page: number) {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(page));
    setSearchParams(next);
  }

  if (!isValid) {
    return (
      <Page title={t('profile.collectionTitle')} description={t('profile.invalidBody')}>
        <ErrorState title={t('profile.invalidTitle')} description={t('profile.invalidBody')} />
      </Page>
    );
  }

  return (
    <Page
      title={collectionQuery.data?.name || t('profile.collectionTitle')}
      eyebrow={profileQuery.data?.nickname || t('profile.eyebrow')}
      description={collectionQuery.data?.note || t('common.noNote')}
      actions={(
        <Button asChild type="button" variant="secondary">
          <Link to={routes.userCollections(userId)}><ArrowLeft className="size-4" /> {t('profile.allCollectionsTitle')}</Link>
        </Button>
      )}
    >
      {profileQuery.isLoading || collectionQuery.isLoading ? <LoadingState title={t('profile.loadingContent')} /> : null}
      {profileQuery.isError || collectionQuery.isError ? <ErrorState title={t('profile.collectionErrorTitle')} description={t('profile.contentErrorBody')} /> : null}
      {collectionQuery.data ? (
        <section className="grid gap-4">
          <div className="flex flex-wrap items-center gap-3 text-sm text-neutral-500 dark:text-neutral-400">
            <Badge variant="accent">{t('common.public')}</Badge>
            <span>{collectionQuery.data.item_count ?? itemsQuery.data?.count ?? 0} {t('common.items')}</span>
            <StarRating value={collectionQuery.data.simple_rating} />
          </div>
          <CommunityTargetActions
            className="rounded-lg border border-neutral-200 bg-white p-2 dark:border-neutral-800 dark:bg-neutral-950"
            reactionCount={numberMeta(collectionQuery.data.reaction_count)}
            reportLabel={t('community.reportCollection')}
            targetId={collectionQuery.data.id}
            targetType="collection"
            viewerState={collectionQuery.data.viewer_state as { has_liked?: boolean; has_bookmarked?: boolean } | undefined}
          />
          {itemsQuery.isLoading ? <LoadingState title={t('profile.loadingCollectionItems')} /> : null}
          {itemsQuery.isError ? <ErrorState title={t('profile.collectionItemsErrorTitle')} description={t('profile.contentErrorBody')} /> : null}
          {!itemsQuery.isLoading && !itemsQuery.isError && items.length === 0 ? (
            <EmptyState title={t('profile.noCollectionItemsTitle')} description={t('profile.noCollectionItemsBody')} />
          ) : null}
          <div className="grid overflow-hidden rounded-lg border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-950">
            {items.map((item) => <CollectionSubjectItem item={item} key={item.id} />)}
          </div>
          <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
          <CommunityCommentsSection targetType="collection" targetId={collectionQuery.data.id} />
        </section>
      ) : null}
    </Page>
  );
}
