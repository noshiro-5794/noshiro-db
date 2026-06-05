import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Star } from 'lucide-react';
import { CommunityContentCard } from '@/features/community/components/CommunityContentCard';
import type { Locale } from '@/features/i18n/messages';
import { useI18n } from '@/features/i18n/use-i18n';
import { socialQueries } from '@/features/social/social-queries';
import type { Collection, CollectionItem, Review, UserSubject } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { Badge } from '@/shared/ui/Badge';

const coverPlaceholder = '/assets/placeholders/subject-cover.png';
const episodeUnit: Record<Locale, string> = {
  'zh-CN': '话',
  'en-US': 'episodes',
  'ja-JP': '話',
};

function formatDate(value?: string, fallback = '') {
  if (!value) return fallback;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function reviewSubjectTitle(review: Review, fallback: string) {
  return review.subject?.display_title || review.subject?.title || review.subject?.title_cn || fallback;
}

function subjectTitle(item: UserSubject, fallback: string) {
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

export function PublicRatingStars({ value, emptyLabel, ratingLabel }: { value?: number | null; emptyLabel: string; ratingLabel: string }) {
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

export function PublicReviewItem({ review }: { review: Review }) {
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
      date={formatDate(review.updated_at || review.created_at, t('common.noDate'))}
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

export function PublicSubjectListItem({ item }: { item: UserSubject }) {
  const { locale, t } = useI18n();

  return (
    <Link className="library-list-item" to={routes.subject(item.subject.id)}>
      <img
        alt=""
        className="h-28 w-[72px] rounded-lg bg-neutral-100 object-cover shadow-sm ring-1 ring-neutral-200 dark:bg-neutral-900 dark:ring-neutral-800 max-sm:h-[86px] max-sm:w-[58px]"
        loading="lazy"
        src={item.subject.image_thumbnail || item.subject.image || coverPlaceholder}
      />
      <span className="grid min-w-0 content-center gap-2">
        <span className="grid min-w-0 gap-1">
          <span className="line-clamp-1 font-semibold text-neutral-950 dark:text-white">{subjectTitle(item, t('common.untitledSubject'))}</span>
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
      </span>
      <span className="grid justify-items-end gap-2 self-center max-sm:col-start-2 max-sm:justify-items-start">
        <Badge variant="secondary">{statusLabel(item.status, t)}</Badge>
        <span className="grid justify-items-end gap-1 text-sm text-neutral-500 dark:text-neutral-400 max-sm:justify-items-start">
          {item.rating ? <strong className="font-semibold text-neutral-950 dark:text-white">{item.rating}</strong> : null}
          <PublicRatingStars emptyLabel={t('library.noSimpleRating')} ratingLabel={t('library.simpleRatingLabel')} value={item.simple_rating} />
        </span>
        {item.updated_at ? <span className="text-xs text-neutral-400">{formatDate(item.updated_at)}</span> : null}
      </span>
    </Link>
  );
}

function PublicCollectionPackCover({ collectionId, userId }: { collectionId: number; userId: number }) {
  const previewQuery = useQuery({
    ...socialQueries.publicCollectionItems(userId, collectionId, { page: 1, page_size: 4 }),
  });
  const previewItems = previewQuery.data?.results ?? [];

  return (
    <div className="collection-pack-cover" aria-hidden>
      {[0, 1, 2, 3].map((slot) => {
        const coverItem = previewItems[slot];
        return (
          <span className="collection-pack-layer" data-slot={slot} key={slot}>
            {coverItem && subjectImage(coverItem) ? <img alt="" src={subjectImage(coverItem) ?? ''} loading="lazy" /> : null}
          </span>
        );
      })}
    </div>
  );
}

export function PublicCollectionPackCard({ collection, userId }: { collection: Collection; userId: number }) {
  const { t } = useI18n();

  return (
    <Link className="collection-pack-card group h-full text-left transition" to={routes.userCollection(userId, collection.id)}>
      <PublicCollectionPackCover collectionId={collection.id} userId={userId} />
      <div className="flex items-start justify-between gap-3">
        <h2 className="min-w-0 truncate text-sm font-semibold">{collection.name}</h2>
        <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-semibold text-neutral-500 dark:bg-neutral-900 dark:text-neutral-400">
          {collection.item_count ?? 0}
        </span>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        {collection.simple_rating ? <PublicRatingStars emptyLabel={t('common.unrated')} ratingLabel={t('library.simpleRatingLabel')} value={collection.simple_rating} /> : <span />}
        <span className="text-xs text-neutral-400">{formatDate(collection.updated_at || collection.created_at)}</span>
      </div>
      {collection.note ? (
        <p className="mt-2 line-clamp-2 text-xs leading-5 text-neutral-500 dark:text-neutral-400">{collection.note}</p>
      ) : null}
    </Link>
  );
}

export function PublicCollectionRailItem({ item }: { item: CollectionItem }) {
  const { t } = useI18n();

  return (
    <div className="collection-rail-card group">
      <Link className="collection-rail-poster" to={routes.subject(item.subject.id)}>
        {subjectImage(item) ? <img src={subjectImage(item) ?? ''} alt="" loading="lazy" /> : <span />}
      </Link>
      <div className="collection-rail-body">
        <Link className="collection-rail-title" to={routes.subject(item.subject.id)}>
          {collectionSubjectTitle(item, t('common.untitledSubject'))}
        </Link>
        <p>{collectionSubjectSubtitle(item, t('common.noMetadata'))}</p>
        <div className="collection-rail-badges">
          {item.relation ? <Badge variant="accent">{item.relation}</Badge> : null}
          {item.user_subject.rating ? <Badge>{item.user_subject.rating}/10</Badge> : null}
        </div>
        {item.user_subject.simple_rating ? (
          <PublicRatingStars emptyLabel={t('common.unrated')} ratingLabel={t('library.simpleRatingLabel')} value={item.user_subject.simple_rating} />
        ) : null}
        {item.user_subject.comment ? <p className="collection-rail-comment">{item.user_subject.comment}</p> : null}
      </div>
    </div>
  );
}
