import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { formatDate } from '@/shared/lib/date';
import { Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Star } from 'lucide-react';
import { CommunityContentCard } from '@/entities/community';
import { CollectionCoverStack } from '@/entities/library';
import { useI18n } from '@/shared/i18n';
import { useVisibleOnce } from '@/shared/lib/use-visible-once';
import { publicUserQueries } from '@/entities/user';
import type { Collection, CollectionItem, Review } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { Badge } from '@/shared/ui/Badge';

const coverPlaceholder = placeholderImagePaths.subjectCover;
function reviewSubjectTitle(review: Review, fallback: string) {
  return review.subject?.display_title || review.subject?.title || review.subject?.title_cn || fallback;
}

function subjectImage(item: CollectionItem) {
  return item.subject.images?.thumbnail || item.subject.image_thumbnail || item.subject.image || null;
}

function collectionSubjectTitle(item: CollectionItem, fallback: string) {
  return item.subject.display_title || item.subject.title || item.subject.title_cn || fallback;
}

function collectionSubjectSubtitle(item: CollectionItem, fallback: string) {
  const parts = [
    item.subject.subject_type,
    item.subject.date,
    item.subject.platform,
    item.user_subject.status ? item.user_subject.status.replaceAll('_', ' ') : null,
  ].filter(Boolean);

  return parts.join(' / ') || fallback;
}

export function PublicRatingStars({
  value,
  emptyLabel,
  ratingLabel,
}: {
  value?: number | null;
  emptyLabel: string;
  ratingLabel: string;
}) {
  if (!value) return <span className="text-sm text-[var(--ui-text-subtle)]">{emptyLabel}</span>;

  return (
    <span aria-label={`${ratingLabel} ${value}/5`} className="flex items-center gap-0.5">
      {Array.from({ length: 5 }, (_, index) => (
        <Star
          className={
            index < value
              ? 'size-4 fill-[var(--ui-accent)] text-[var(--ui-accent)]'
              : 'size-4 text-[var(--ui-border-strong)]'
          }
          key={index}
        />
      ))}
    </span>
  );
}

export function PublicReviewItem({ review }: { review: Review }) {
  const { t } = useI18n();

  return (
    <CommunityContentCard
      badges={
        <>
          <Badge variant="accent">{t('common.public')}</Badge>
          {review.is_spoiler ? <Badge>{t('common.spoiler')}</Badge> : null}
        </>
      }
      body={review.content || t('common.noContent')}
      cover={review.subject?.image_thumbnail || review.subject?.image || coverPlaceholder}
      date={formatDate(review.updated_at || review.created_at, t('common.noDate'))}
      href={routes.review(review.id)}
      isSpoiler={review.is_spoiler}
      subject={
        review.subject
          ? {
              href: routes.entity(review.subject.id),
              title: reviewSubjectTitle(review, t('common.untitledSubject')),
            }
          : undefined
      }
      title={review.title || t('common.untitled')}
      typeLabel={t('community.targetType.review')}
    />
  );
}

function PublicCollectionPackCover({
  collectionId,
  hasItems,
  userId,
}: {
  collectionId: number;
  hasItems: boolean;
  userId: number;
}) {
  const { isVisible, ref } = useVisibleOnce();
  const previewQuery = useQuery({
    ...publicUserQueries.publicCollectionItems(userId, collectionId, { page: 1, page_size: 4 }),
    enabled: hasItems && isVisible,
  });
  const previewItems = previewQuery.data?.results ?? [];
  const images = previewItems.map(subjectImage);

  return <CollectionCoverStack images={images} ref={ref} />;
}

export function PublicCollectionPackCard({ collection, userId }: { collection: Collection; userId: number }) {
  const { t } = useI18n();

  return (
    <Link
      className="grid h-full min-w-0 gap-3 rounded-md border border-border bg-surface p-3.5 text-left text-foreground transition-colors hover:border-[var(--ui-accent-border)] hover:bg-muted"
      data-slot="public-collection-card"
      to={routes.userCollection(userId, collection.id)}
    >
      <PublicCollectionPackCover
        collectionId={collection.id}
        hasItems={(collection.item_count ?? 0) > 0}
        userId={userId}
      />
      <div className="flex items-start justify-between gap-3">
        <h3 className="min-w-0 truncate text-sm font-semibold">{collection.name}</h3>
        <Badge className="tabular-nums">{collection.item_count ?? 0}</Badge>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        {collection.simple_rating ? (
          <PublicRatingStars
            emptyLabel={t('common.unrated')}
            ratingLabel={t('library.simpleRatingLabel')}
            value={collection.simple_rating}
          />
        ) : (
          <span />
        )}
        <span className="text-xs text-[var(--ui-text-subtle)]">
          {formatDate(collection.updated_at || collection.created_at)}
        </span>
      </div>
      {collection.note ? (
        <p className="mt-2 line-clamp-2 text-xs leading-5 text-[var(--ui-text-muted)]">{collection.note}</p>
      ) : null}
    </Link>
  );
}

export function PublicCollectionItemCard({ item }: { item: CollectionItem }) {
  const { t } = useI18n();
  const image = subjectImage(item) || coverPlaceholder;

  return (
    <article className="grid min-w-0 content-start gap-3" data-slot="public-collection-item">
      <Link
        aria-label={collectionSubjectTitle(item, t('common.untitledSubject'))}
        className="block aspect-[2/3] overflow-hidden rounded-sm border border-border bg-muted transition-[border-color,box-shadow] hover:border-[var(--ui-accent-border)] hover:shadow-[var(--ui-shadow-surface)]"
        to={routes.entity(item.subject.id)}
      >
        <img
          alt=""
          className="size-full object-cover"
          decoding="async"
          loading="lazy"
          referrerPolicy="no-referrer"
          src={image}
        />
      </Link>
      <div className="grid min-w-0 gap-2">
        <h3 className="m-0 text-sm font-semibold leading-5 text-foreground">
          <Link
            className="line-clamp-2 transition-colors hover:text-[var(--ui-accent-text)]"
            to={routes.entity(item.subject.id)}
          >
            {collectionSubjectTitle(item, t('common.untitledSubject'))}
          </Link>
        </h3>
        <p className="line-clamp-2 text-xs leading-5 text-muted-foreground">
          {collectionSubjectSubtitle(item, t('common.noMetadata'))}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {item.relation ? <Badge variant="accent">{item.relation}</Badge> : null}
          {item.user_subject.rating ? <Badge variant="secondary">{item.user_subject.rating}/10</Badge> : null}
        </div>
        {item.user_subject.simple_rating ? (
          <PublicRatingStars
            emptyLabel={t('common.unrated')}
            ratingLabel={t('library.simpleRatingLabel')}
            value={item.user_subject.simple_rating}
          />
        ) : null}
        {item.user_subject.comment ? (
          <p className="line-clamp-3 border-l-2 border-[var(--ui-accent-border)] pl-2 text-xs leading-5 text-muted-foreground">
            {item.user_subject.comment}
          </p>
        ) : null}
      </div>
    </article>
  );
}
