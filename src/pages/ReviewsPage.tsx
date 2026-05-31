import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { libraryQueries } from '@/features/library/library-queries';
import { routes } from '@/routes/paths';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

export function ReviewsPage() {
  const reviewsQuery = useQuery(libraryQueries.reviews({ page_size: 20, ordering: '-created_at' }));

  return (
    <Page title="Reviews" eyebrow="Marked" description="Your long-form Markdown reviews and drafts.">
      {reviewsQuery.isLoading ? <LoadingState title="Loading reviews" /> : null}
      {reviewsQuery.isError ? <ErrorState title="Unable to load reviews." description="Please try again later." /> : null}
      {!reviewsQuery.isLoading && !reviewsQuery.isError && reviewsQuery.data?.results.length === 0 ? (
        <EmptyState title="No reviews yet." description="Reviews will be created from subject pages." />
      ) : null}
      <div className="grid gap-3">
        {(reviewsQuery.data?.results ?? []).map((review) => (
          <Link
            className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm transition hover:border-[var(--color-accent-border)] dark:border-neutral-800 dark:bg-neutral-950"
            key={review.id}
            to={review.subject ? routes.subject(review.subject.id) : routes.reviews}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h2 className="line-clamp-1 font-semibold text-neutral-950 dark:text-white">{review.title}</h2>
                <p className="mt-1 line-clamp-1 text-sm text-neutral-500 dark:text-neutral-400">
                  {review.subject?.display_title || review.subject?.title || 'Untitled subject'}
                </p>
              </div>
              <span className="rounded-full bg-neutral-100 px-2 py-1 text-xs font-semibold text-neutral-500 dark:bg-neutral-900 dark:text-neutral-400">
                {review.is_public ? 'Public' : 'Private'}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </Page>
  );
}
