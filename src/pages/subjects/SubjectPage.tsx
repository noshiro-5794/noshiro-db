import { useState } from 'react';
import { getRouteApi, Link, useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Network } from 'lucide-react';
import { useAuth } from '@/entities/session';
import { useI18n } from '@/shared/i18n';
import { libraryQueries } from '@/entities/library';
import { subjectQueries } from '@/entities/subject';
import {
  CharactersSection,
  EpisodesSection,
  MarkEditorDialog,
  metaOf,
  seoDescriptionOf,
  seoImageOf,
  RelationsSection,
  PublicReviewsSection,
  SubjectDescriptionSection,
  SubjectMarkSection,
  SubjectReviewSection,
  SubjectSectionNav,
  SubjectSidebar,
  titleOf,
} from '@/features/subject-detail';
import { parseUuid } from '@/shared/lib/validation';
import { routes } from '@/shared/routing/paths';
import { currentRoutePath, routeBackState } from '@/shared/routing/route-state';
import { Seo } from '@/shared/seo/Seo';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

const subjectRoute = getRouteApi('/entities/$subjectId');

export function SubjectPage() {
  const { t } = useI18n();
  const params = subjectRoute.useParams();
  const subjectId = parseUuid(params.subjectId);
  const location = useLocation();
  const auth = useAuth();
  const isAuthenticated = auth.isAuthenticated;
  const [isMarkDialogOpen, setIsMarkDialogOpen] = useState(false);

  const detailQuery = useQuery({
    ...subjectQueries.detail(subjectId ?? ''),
    enabled: Boolean(subjectId),
  });
  const contextQuery = useQuery({
    ...libraryQueries.subjectContext(subjectId ?? ''),
    enabled: Boolean(subjectId) && isAuthenticated,
  });
  const progressQuery = useQuery({
    ...libraryQueries.progress(subjectId ?? ''),
    enabled: Boolean(subjectId) && isAuthenticated,
  });

  const userSubject = contextQuery.data?.user_subject ?? null;
  const progress = progressQuery.data ?? contextQuery.data?.progress;

  if (!subjectId) {
    return (
      <Page title={t('subject.title')} eyebrow={t('subject.title')}>
        <EmptyState title={t('subject.missingTitle')} description={t('subject.missingBody')} />
      </Page>
    );
  }

  if (detailQuery.isLoading) {
    return (
      <Page title={t('subject.title')} eyebrow={t('subject.title')}>
        <LoadingState title={t('subject.loadingTitle')} />
      </Page>
    );
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <Page title={t('subject.title')} eyebrow={t('subject.title')}>
        <ErrorState title={t('subject.errorTitle')} description={t('subject.errorBody')} />
      </Page>
    );
  }

  const subject = detailQuery.data;
  const finishedPrimaryCount = progress?.finished_count ?? 0;
  const totalPrimaryCount = progress?.total_episodes ?? subject.episode_count;
  const anchorScrollClass = 'scroll-mt-[calc(var(--ui-sticky-content-top)+3rem)]';
  const overviewSectionClass = `${anchorScrollClass} border-t-0 pt-0`;
  const detailLinkState = routeBackState(location, titleOf(subject, t('common.untitledSubject')));
  const loginState = { returnTo: currentRoutePath(location) };

  return (
    <Page
      title={titleOf(subject, t('common.untitledSubject'))}
      eyebrow={t('subject.title')}
      description={metaOf(subject)}
      seo={false}
      actions={
        <Button
          asChild
          aria-label={t('subject.graph')}
          className="border-[var(--ui-accent-border)] text-[var(--ui-accent-text)] hover:bg-[var(--ui-accent-soft)]"
          size="icon"
          tooltip={t('subject.graph')}
          type="button"
          variant="secondary"
        >
          <Link params={{ subjectId: subject.id }} title={t('subject.graph')} to="/entities/$subjectId/graph">
            <Network className="size-4" />
          </Link>
        </Button>
      }
    >
      <Seo
        title={titleOf(subject, t('common.untitledSubject'))}
        description={seoDescriptionOf(subject)}
        image={seoImageOf(subject)}
        path={routes.entity(subject.id)}
      />
      <SubjectSectionNav />
      <div className="grid items-start gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
        <div className="order-2 min-w-0 lg:order-1">
          <SubjectSidebar key={subject.id} subject={subject} />
        </div>

        <div className="order-1 grid gap-5 self-start lg:order-2">
          <div className="grid gap-x-6 gap-y-5 lg:grid-cols-2">
            <SubjectMarkSection
              className={overviewSectionClass}
              context={contextQuery.data}
              finishedCount={finishedPrimaryCount}
              isAuthenticated={isAuthenticated}
              isError={contextQuery.isError}
              isLoading={contextQuery.isLoading}
              loginState={loginState}
              totalCount={totalPrimaryCount}
              onEdit={() => {
                setIsMarkDialogOpen(true);
              }}
              onRetry={() => void contextQuery.refetch()}
            />
            <SubjectReviewSection
              canCreateReview={Boolean(userSubject)}
              className={overviewSectionClass}
              detailLinkState={detailLinkState}
              isError={isAuthenticated && contextQuery.isError}
              isLoading={isAuthenticated && contextQuery.isLoading}
              reviews={contextQuery.data?.reviews ?? []}
              subjectId={subjectId}
              onRetry={() => void contextQuery.refetch()}
            />
          </div>

          <EpisodesSection
            key={subject.id}
            className={anchorScrollClass}
            progress={progress}
            subject={subject}
            userSubjectExists={Boolean(userSubject)}
          />

          <SubjectDescriptionSection className={anchorScrollClass} subject={subject} />

          <CharactersSection key={`characters:${subject.id}`} className={anchorScrollClass} subjectId={subject.id} />

          <RelationsSection
            key={`relations:${subject.id}`}
            className={anchorScrollClass}
            subjectId={subject.id}
            subjectTitle={titleOf(subject, t('common.untitledSubject'))}
          />

          <PublicReviewsSection
            key={`public-reviews:${subject.id}`}
            className={anchorScrollClass}
            subjectId={subject.id}
            subjectTitle={titleOf(subject, t('common.untitledSubject'))}
          />
        </div>
      </div>
      <MarkEditorDialog
        context={contextQuery.data}
        open={isMarkDialogOpen}
        subjectId={subjectId}
        totalEpisodeCount={totalPrimaryCount}
        onOpenChange={setIsMarkDialogOpen}
      />
    </Page>
  );
}
