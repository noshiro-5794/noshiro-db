import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { formatDate } from '@/shared/lib/date';
import { Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { ShieldCheck } from 'lucide-react';
import { libraryQueries } from '@/entities/library';
import { useI18n } from '@/shared/i18n';
import type { CurrentUserProfile, UserSubject } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { ErrorState } from '@/shared/ui/FeedbackState';
import { UserActivityFeed } from './UserActivityFeed';
import './home.css';

const avatarPlaceholder = placeholderImagePaths.avatar;

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

function ListSkeleton({ rows = 3, showMedia = true }: { rows?: number; showMedia?: boolean }) {
  return (
    <div aria-hidden="true" className="grid gap-2 px-2 pb-2">
      {Array.from({ length: rows }, (_, index) => (
        <div className="flex animate-pulse items-center gap-2.5 rounded-sm px-2 py-2" key={index}>
          {showMedia ? <span className="size-9 shrink-0 rounded-sm bg-muted" /> : null}
          <span className="grid min-w-0 flex-1 gap-2">
            <span className="h-3.5 w-2/3 rounded-sm bg-muted" />
            <span className="h-3 w-1/3 rounded-sm bg-muted" />
          </span>
        </div>
      ))}
    </div>
  );
}

export function UserHome({ isAdmin, profile }: { isAdmin: boolean; profile: CurrentUserProfile | null }) {
  const { t } = useI18n();
  const recentSubjectsQuery = useQuery(libraryQueries.userSubjects({ page_size: 4, ordering: '-updated_at' }));
  const watchingSubjectsQuery = useQuery(
    libraryQueries.userSubjects({ status: 'doing', page_size: 3, ordering: '-updated_at' }),
  );
  const reviewsQuery = useQuery(libraryQueries.reviews({ page_size: 3, ordering: '-created_at' }));
  const collectionsQuery = useQuery(libraryQueries.collections({ page_size: 4, ordering: '-id' }));
  const recentSubjects = recentSubjectsQuery.data?.results ?? [];
  const watchingSubjects = watchingSubjectsQuery.data?.results ?? [];
  const reviews = (reviewsQuery.data?.results ?? []).slice(0, 3);
  const collections = (collectionsQuery.data?.results ?? []).slice(0, 4);

  return (
    <div className="home-shell">
      <section className="home-overview" data-slot="dashboard-overview">
        <div className="home-overview-main">
          <div className="flex min-w-0 items-center gap-3.5">
            <img
              alt=""
              className="home-avatar"
              decoding="async"
              referrerPolicy="no-referrer"
              src={profile?.avatar || avatarPlaceholder}
            />
            <div className="min-w-0">
              <div className="flex min-w-0 flex-wrap items-center gap-2">
                <p className="home-kicker">{t('home.welcomeBack')}</p>
                {isAdmin ? <Badge variant="secondary">{t('auth.admin')}</Badge> : null}
              </div>
              <h2 className="home-overview-title">{profile?.nickname || t('common.anonymous')}</h2>
            </div>
          </div>
        </div>
        <div className="home-stat-grid">
          {[
            { label: t('home.marked'), value: recentSubjectsQuery.data?.count ?? 0, href: routes.library },
            { label: t('status.doing'), value: watchingSubjectsQuery.data?.count ?? 0, href: routes.library },
            { label: t('common.reviews'), value: reviewsQuery.data?.count ?? 0, href: routes.reviews },
          ].map((item) => (
            <Link className="home-stat" key={item.label} to={item.href}>
              <strong>{item.value}</strong>
              <span>{item.label}</span>
            </Link>
          ))}
        </div>
      </section>

      {isAdmin ? (
        <section className="home-admin-panel">
          <div className="home-admin-content">
            <span className="home-panel-icon">
              <ShieldCheck className="size-5" />
            </span>
            <div className="min-w-0">
              <p className="home-admin-meta">{t('auth.admin')}</p>
              <h2 className="home-admin-title">{t('admin.syncTitle')}</h2>
            </div>
          </div>
          <Button asChild className="home-admin-action" size="sm" variant="secondary">
            <Link to={routes.admin}>
              <ShieldCheck className="size-4" />
              {t('nav.admin')}
            </Link>
          </Button>
        </section>
      ) : null}

      <div className="home-layout">
        <div className="home-main">
          <UserActivityFeed />
          <section className="home-card-grid">
            <div className="home-panel">
              <div className="home-section-header">
                <h2>{t('home.recentMarks')}</h2>
                <Link className="text-sm font-semibold text-[var(--ui-accent-text)]" to={routes.library}>
                  {t('home.viewLibrary')}
                </Link>
              </div>
              <div className="home-list">
                {recentSubjectsQuery.isLoading ? <ListSkeleton rows={4} /> : null}
                {recentSubjects.map((item) => (
                  <Link className="home-list-item is-mark" key={item.id} to={routes.subject(item.subject.id)}>
                    <img
                      alt=""
                      decoding="async"
                      loading="lazy"
                      referrerPolicy="no-referrer"
                      src={item.subject.image_thumbnail || item.subject.image || placeholderImagePaths.subjectCover}
                    />
                    <span className="min-w-0">
                      <span className="home-list-title">{subjectTitle(item, t('common.untitledSubject'))}</span>
                      <span className="home-list-meta">{formatDate(item.updated_at || item.created_at)}</span>
                    </span>
                    <Badge variant="secondary">{statusLabel(item.status, t)}</Badge>
                  </Link>
                ))}
                {recentSubjectsQuery.isError ? (
                  <ErrorState title={t('home.marksErrorTitle')} description={t('home.marksErrorBody')} />
                ) : null}
                {!recentSubjectsQuery.isLoading && !recentSubjectsQuery.isError && recentSubjects.length === 0 ? (
                  <p className="home-empty-line">{t('home.noMarks')}</p>
                ) : null}
              </div>
            </div>

            <div className="home-panel">
              <div className="home-section-header">
                <h2>{t('home.latestReviews')}</h2>
                <Link className="text-sm font-semibold text-[var(--ui-accent-text)]" to={routes.reviews}>
                  {t('home.viewAll')}
                </Link>
              </div>
              <div className="home-list">
                {reviewsQuery.isLoading ? <ListSkeleton rows={3} showMedia={false} /> : null}
                {reviews.map((review) => (
                  <Link className="home-review-row" key={review.id} to={routes.review(review.id)}>
                    <p>{review.title}</p>
                    <span>{review.content || t('common.noContent')}</span>
                  </Link>
                ))}
                {reviewsQuery.isError ? (
                  <ErrorState title={t('reviews.errorTitle')} description={t('search.errorBody')} />
                ) : null}
                {!reviewsQuery.isLoading && !reviewsQuery.isError && reviews.length === 0 ? (
                  <p className="home-empty-line">{t('home.noReviews')}</p>
                ) : null}
              </div>
            </div>
          </section>
        </div>

        <aside className="home-rail">
          <section className="home-panel">
            <div className="home-section-header">
              <h2>{t('home.continue')}</h2>
              <Link className="text-sm font-semibold text-[var(--ui-accent-text)]" to={routes.library}>
                {t('home.viewLibrary')}
              </Link>
            </div>
            <div className="home-list is-compact">
              {watchingSubjectsQuery.isLoading ? <ListSkeleton rows={3} /> : null}
              {watchingSubjects.map((item) => (
                <Link className="home-list-item" key={item.id} to={routes.subject(item.subject.id)}>
                  <img
                    alt=""
                    decoding="async"
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    src={item.subject.image_thumbnail || item.subject.image || placeholderImagePaths.subjectCover}
                  />
                  <span className="grid min-w-0 content-center">
                    <span className="home-list-title">{subjectTitle(item, t('common.untitledSubject'))}</span>
                    <span className="home-list-meta">
                      {item.rating ? `${item.rating} / 10` : statusLabel(item.status, t)}
                    </span>
                  </span>
                </Link>
              ))}
              {watchingSubjectsQuery.isError ? (
                <ErrorState title={t('home.marksErrorTitle')} description={t('home.marksErrorBody')} />
              ) : null}
              {!watchingSubjectsQuery.isLoading && !watchingSubjectsQuery.isError && watchingSubjects.length === 0 ? (
                <p className="home-empty-line">{t('home.noWatching')}</p>
              ) : null}
            </div>
          </section>

          <section className="home-panel">
            <div className="home-section-header">
              <h2>{t('nav.collections')}</h2>
            </div>
            <div className="home-list is-compact">
              {collectionsQuery.isLoading ? <ListSkeleton rows={4} showMedia={false} /> : null}
              {collections.map((collection) => (
                <Link className="home-collection-row" key={collection.id} to={routes.collections}>
                  <p>{collection.name}</p>
                  <span>
                    {collection.item_count ?? 0} {t('common.items')}
                  </span>
                </Link>
              ))}
              {collectionsQuery.isError ? (
                <ErrorState title={t('collections.errorTitle')} description={t('search.errorBody')} />
              ) : null}
              {!collectionsQuery.isLoading && !collectionsQuery.isError && collections.length === 0 ? (
                <p className="home-empty-line">{t('home.noCollections')}</p>
              ) : null}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
