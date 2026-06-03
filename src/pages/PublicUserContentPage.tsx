import { type FormEvent, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, BookOpen, FileText, Library, Search, Star } from 'lucide-react';
import { CommunityContentCard } from '@/features/community/components/CommunityContentCard';
import { useI18n } from '@/features/i18n/use-i18n';
import { socialQueries } from '@/features/social/social-queries';
import type { Collection, Review, UserSubject } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 12;
const coverPlaceholder = '/assets/placeholders/subject-cover.png';

type PublicUserContentMode = 'reviews' | 'subjects' | 'collections';

type PublicUserContentPageProps = {
  mode: PublicUserContentMode;
};

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function subjectTitle(item: UserSubject, fallback: string) {
  return item.subject.display_title || item.subject.title || item.subject.title_cn || fallback;
}

function statusLabel(status: string | undefined, t: ReturnType<typeof useI18n>['t']) {
  const labels: Record<string, string> = {
    wish: t('status.wish'),
    doing: t('status.doing'),
    done: t('status.done'),
    on_hold: t('status.onHold'),
    drop: t('status.drop'),
  };
  return labels[status ?? ''] ?? status?.replaceAll('_', ' ') ?? t('status.marked');
}

function reviewSubjectTitle(review: Review, fallback: string) {
  return review.subject?.display_title || review.subject?.title || review.subject?.title_cn || fallback;
}

function StarRating({ value }: { value: number | null }) {
  if (!value) return null;

  return (
    <span className="inline-flex items-center gap-0.5 text-[var(--color-accent-strong)]" aria-label={`${value} / 5`}>
      {Array.from({ length: 5 }, (_, index) => (
        <Star className={`size-3.5 ${index < value ? 'fill-current' : 'text-neutral-300 dark:text-neutral-700'}`} key={index} />
      ))}
    </span>
  );
}

function ReviewItem({ review }: { review: Review }) {
  const { t } = useI18n();

  return (
    <CommunityContentCard
      badges={(
        <>
          <Badge variant="accent">{t('common.public')}</Badge>
          {review.is_spoiler ? <Badge>{t('common.spoiler')}</Badge> : null}
        </>
      )}
      body={review.content || t('common.noContent')}
      cover={review.subject?.image_thumbnail || review.subject?.image || coverPlaceholder}
      date={formatDate(review.updated_at || review.created_at) || t('common.noDate')}
      href={routes.review(review.id)}
      isSpoiler={review.is_spoiler}
      subject={review.subject ? {
        href: routes.subject(review.subject.id),
        title: reviewSubjectTitle(review, t('common.untitledSubject')),
      } : undefined}
      title={review.title || t('common.untitled')}
      typeLabel={t('community.targetType.review')}
    />
  );
}

function SubjectItem({ item }: { item: UserSubject }) {
  const { t } = useI18n();

  return (
    <CommunityContentCard
      badges={(
        <>
          <Badge variant="secondary">{statusLabel(item.status, t)}</Badge>
          <StarRating value={item.simple_rating} />
        </>
      )}
      body={item.comment || item.subject.display_subtitle || item.subject.platform || ''}
      cover={item.subject.image_thumbnail || item.subject.image || coverPlaceholder}
      date={formatDate(item.updated_at || item.created_at) || t('common.noDate')}
      href={routes.subject(item.subject.id)}
      title={subjectTitle(item, t('common.untitledSubject'))}
      typeLabel={item.subject.subject_type}
    />
  );
}

function CollectionItem({ collection, userId }: { collection: Collection; userId: number }) {
  const { t } = useI18n();

  return (
    <CommunityContentCard
      badges={(
        <>
          <Badge variant="secondary">{collection.item_count ?? 0} {t('common.items')}</Badge>
          <StarRating value={collection.simple_rating} />
        </>
      )}
      body={collection.note || t('common.noNote')}
      date={formatDate(collection.updated_at || collection.created_at) || t('common.noDate')}
      href={routes.userCollection(userId, collection.id)}
      icon={<BookOpen className="size-4" />}
      title={collection.name}
      typeLabel={t('community.targetType.collection')}
    />
  );
}

function modeTitle(mode: PublicUserContentMode, t: ReturnType<typeof useI18n>['t']) {
  if (mode === 'reviews') return t('profile.allReviewsTitle');
  if (mode === 'subjects') return t('profile.allSubjectsTitle');
  return t('profile.allCollectionsTitle');
}

function modeEmptyTitle(mode: PublicUserContentMode, t: ReturnType<typeof useI18n>['t']) {
  if (mode === 'reviews') return t('profile.noReviewsTitle');
  if (mode === 'subjects') return t('profile.noSubjectsTitle');
  return t('profile.noCollectionsTitle');
}

function modeEmptyBody(mode: PublicUserContentMode, t: ReturnType<typeof useI18n>['t']) {
  if (mode === 'reviews') return t('profile.noReviewsBody');
  if (mode === 'subjects') return t('profile.noSubjectsBody');
  return t('profile.noCollectionsBody');
}

function modeIcon(mode: PublicUserContentMode) {
  if (mode === 'reviews') return <FileText className="size-4" />;
  if (mode === 'subjects') return <Library className="size-4" />;
  return <BookOpen className="size-4" />;
}

export function PublicUserContentPage({ mode }: PublicUserContentPageProps) {
  const { t } = useI18n();
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const userId = Number(params.userId);
  const isValidUserId = Number.isFinite(userId) && userId > 0;
  const keyword = searchParams.get('keyword') ?? '';
  const ordering = searchParams.get('ordering') ?? (mode === 'subjects' ? '-updated_at' : mode === 'reviews' ? '-created_at' : '-id');
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
  const [draftKeyword, setDraftKeyword] = useState(keyword);

  const reviewOrderingOptions = [
    { label: t('reviews.sortNewest'), value: '-created_at' },
    { label: t('reviews.sortOldest'), value: 'created_at' },
  ];
  const subjectOrderingOptions = [
    { label: t('library.sortRecentlyUpdated'), value: '-updated_at' },
    { label: t('library.sortRecentlyAdded'), value: '-created_at' },
    { label: t('library.sortRatingHigh'), value: '-rating' },
    { label: t('library.sortSimpleRatingHigh'), value: '-simple_rating' },
  ];
  const collectionOrderingOptions = [
    { label: t('collections.sortNewest'), value: '-id' },
    { label: t('collections.sortOldest'), value: 'id' },
    { label: t('collections.sortNameAsc'), value: 'name' },
    { label: t('collections.sortMostItems'), value: '-item_count' },
  ];
  const orderingOptions = mode === 'reviews' ? reviewOrderingOptions : mode === 'subjects' ? subjectOrderingOptions : collectionOrderingOptions;

  const profileQuery = useQuery({ ...socialQueries.publicProfile(userId), enabled: isValidUserId });
  const reviewsQuery = useQuery({
    ...socialQueries.publicReviews(userId, {
      keyword: keyword || undefined,
      ordering: ordering as 'created_at' | '-created_at' | 'id' | '-id',
      page: currentPage,
      page_size: pageSize,
    }),
    enabled: isValidUserId && mode === 'reviews',
  });
  const subjectsQuery = useQuery({
    ...socialQueries.publicSubjects(userId, {
      keyword: keyword || undefined,
      ordering,
      page: currentPage,
      page_size: pageSize,
    }),
    enabled: isValidUserId && mode === 'subjects',
  });
  const collectionsQuery = useQuery({
    ...socialQueries.publicCollections(userId, {
      keyword: keyword || undefined,
      ordering: ordering as 'id' | '-id' | 'name' | '-name' | 'simple_rating' | '-simple_rating' | 'item_count' | '-item_count',
      page: currentPage,
      page_size: pageSize,
    }),
    enabled: isValidUserId && mode === 'collections',
  });

  const activeQuery = mode === 'reviews' ? reviewsQuery : mode === 'subjects' ? subjectsQuery : collectionsQuery;
  const totalCount = activeQuery.data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  function updateSearchParam(key: string, value: string) {
    setSearchParams((currentParams) => {
      const nextParams = new URLSearchParams(currentParams);
      if (value) nextParams.set(key, value);
      else nextParams.delete(key);
      if (key !== 'page') nextParams.delete('page');
      return nextParams;
    });
  }

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateSearchParam('keyword', draftKeyword.trim());
  }

  if (!isValidUserId) {
    return (
      <Page title={modeTitle(mode, t)} description={t('profile.invalidBody')}>
        <ErrorState title={t('profile.invalidTitle')} description={t('profile.invalidBody')} />
      </Page>
    );
  }

  return (
    <Page
      title={modeTitle(mode, t)}
      eyebrow={t('profile.eyebrow')}
      description={profileQuery.data?.nickname ? `${profileQuery.data.nickname} · ${totalCount}` : t('profile.contentDescription')}
      actions={(
        <Button asChild type="button" variant="secondary">
          <Link to={routes.userProfile(userId)}><ArrowLeft className="size-4" /> {t('profile.backToProfile')}</Link>
        </Button>
      )}
    >
      <form className="reviews-toolbar" onSubmit={handleSearch}>
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_190px_auto]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-400" />
            <Input className="pl-9" value={draftKeyword} placeholder={t('profile.contentSearchPlaceholder')} onChange={(event) => setDraftKeyword(event.target.value)} />
          </div>
          <FilterMenu label={t('common.sort')} options={orderingOptions} value={ordering} onChange={(value) => updateSearchParam('ordering', value)} />
          <Button type="submit">{t('common.search')}</Button>
        </div>
      </form>

      <div className="flex items-center justify-between gap-3 text-sm text-neutral-500 dark:text-neutral-400">
        <span className="inline-flex items-center gap-2">{modeIcon(mode)} {totalCount}</span>
        {activeQuery.isFetching ? <span>{t('common.loading')}</span> : null}
      </div>

      {profileQuery.isLoading || activeQuery.isLoading ? <LoadingState title={t('profile.loadingContent')} /> : null}
      {profileQuery.isError || activeQuery.isError ? <ErrorState title={t('profile.contentErrorTitle')} description={t('profile.contentErrorBody')} /> : null}
      {!activeQuery.isLoading && !activeQuery.isError && totalCount === 0 ? (
        <EmptyState title={modeEmptyTitle(mode, t)} description={modeEmptyBody(mode, t)} />
      ) : null}

      {mode === 'reviews' ? (
        <div className="review-list">
          {(reviewsQuery.data?.results ?? []).map((review) => <ReviewItem key={review.id} review={review} />)}
        </div>
      ) : null}

      {mode === 'subjects' ? (
        <div className="grid gap-3">
          {(subjectsQuery.data?.results ?? []).map((item) => <SubjectItem key={item.id} item={item} />)}
        </div>
      ) : null}

      {mode === 'collections' ? (
        <div className="grid gap-3">
          {(collectionsQuery.data?.results ?? []).map((collection) => <CollectionItem key={collection.id} collection={collection} userId={userId} />)}
        </div>
      ) : null}

      <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={(page) => updateSearchParam('page', String(page))} />
    </Page>
  );
}
