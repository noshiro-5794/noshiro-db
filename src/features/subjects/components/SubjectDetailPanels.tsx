import { lazy, Suspense } from 'react';
import type { ApiPage, Review, SubjectDetail, SubjectEpisode, SubjectRelation, SubjectRelationList } from '@/lib/api/types';

const coverPlaceholder = '/assets/placeholders/subject-cover.png';
const MarkdownRenderer = lazy(() =>
  import('@/features/reviews/components/MarkdownRenderer').then((module) => ({
    default: module.MarkdownRenderer,
  })),
);

type SubjectOverviewProps = {
  subject: SubjectDetail;
};

export function SubjectOverview({ subject }: SubjectOverviewProps) {
  return (
    <section className="panel panel-large">
      <span className="panel-kicker">Overview</span>
      <h2>{subject.title}</h2>
      <p>{subject.summary || 'No summary has been provided by the backend yet.'}</p>
      {subject.tags?.length ? (
        <div className="tag-row">
          {subject.tags.slice(0, 8).map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function SubjectSidebar({ subject }: SubjectOverviewProps) {
  return (
    <aside className="subject-side">
      <img className="subject-poster" src={subject.image || subject.image_thumbnail || coverPlaceholder} alt="" />
      <div className="panel compact-panel">
        <span className="panel-kicker">Personal</span>
        <h2>Not marked</h2>
        <p>Login-bound status, rating, tags, and progress controls will live here.</p>
      </div>
    </aside>
  );
}

type SubjectStatsGridProps = {
  subject: SubjectDetail;
  episodes?: ApiPage<SubjectEpisode>;
};

export function SubjectStatsGrid({ subject, episodes }: SubjectStatsGridProps) {
  return (
    <section className="detail-grid">
      <div className="panel">
        <span className="panel-kicker">Episodes</span>
        <h2>{subject.episode_count}</h2>
        <p>
          {episodes
            ? `${episodes.results.length} loaded for the first page.`
            : 'Episode list module placeholder.'}
        </p>
      </div>
      <div className="panel">
        <span className="panel-kicker">Staff</span>
        <h2>{subject.staff_count}</h2>
        <p>Staff and character tabs will be added after the skeleton is stable.</p>
      </div>
      <div className="panel">
        <span className="panel-kicker">Characters</span>
        <h2>{subject.character_count}</h2>
        <p>Character cards can reuse the same compact media component later.</p>
      </div>
    </section>
  );
}

type SubjectRelationsPanelProps = {
  isFetching: boolean;
  relations?: SubjectRelationList;
};

function flattenRelations(relations?: SubjectRelationList): SubjectRelation[] {
  return [...(relations?.outgoing ?? []), ...(relations?.incoming ?? [])];
}

export function SubjectRelationsPanel({ isFetching, relations }: SubjectRelationsPanelProps) {
  const items = flattenRelations(relations);

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <span className="panel-kicker">Related</span>
          <h2>Relations</h2>
        </div>
        {isFetching ? <span>Loading</span> : null}
      </div>
      <div className="relation-list">
        {items.slice(0, 5).map((relation) => (
          <span key={`${relation.relation}-${relation.subject.id}`}>
            <strong>{relation.relation}</strong>
            {relation.subject.title_cn || relation.subject.title}
          </span>
        ))}
        {!isFetching && items.length === 0 ? <p>No relations returned yet.</p> : null}
      </div>
    </section>
  );
}

type SubjectReviewPanelProps = {
  isAuthenticated: boolean;
  isFetching: boolean;
  reviews?: Review[];
};

export function SubjectReviewPanel({ isAuthenticated, isFetching, reviews = [] }: SubjectReviewPanelProps) {
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <span className="panel-kicker">Reviews</span>
          <h2>Markdown reviews</h2>
        </div>
        {isFetching ? <span>Loading</span> : null}
      </div>
      {!isAuthenticated ? <p>Log in to view and manage your reviews for this subject.</p> : null}
      {isAuthenticated && !isFetching && reviews.length === 0 ? <p>No reviews have been created for this subject yet.</p> : null}
      <div className="grid gap-4">
        {reviews.map((review) => (
          <article className="rounded-lg border border-[color:var(--color-border)] p-4" key={review.id}>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-lg font-semibold text-[var(--color-text)]">{review.title}</h3>
              <span className="text-xs text-neutral-500 dark:text-neutral-400">
                {review.is_public ? 'Public' : 'Private'}
                {review.is_spoiler ? ' · Spoiler' : ''}
              </span>
            </div>
            <Suspense fallback={<p className="text-sm text-neutral-500 dark:text-neutral-400">Rendering Markdown...</p>}>
              <MarkdownRenderer content={review.content} />
            </Suspense>
          </article>
        ))}
      </div>
    </section>
  );
}
