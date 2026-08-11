import { useState } from 'react';
import { getRouteApi, Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { MessageSquare } from 'lucide-react';
import {
  activityBody,
  activityTargetHref,
  activityTitle,
  activityTypeLabel,
  communityQueries,
  CommunityContentCard,
} from '@/entities/community';
import { CommunityCommentsSection, CommunityTargetActions } from '@/features/community';
import { useI18n } from '@/shared/i18n';
import { formatDate } from '@/shared/lib/date';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState } from '@/shared/ui/FeedbackState';
import { Toggle } from '@/shared/ui/Toggle';

const homeRoute = getRouteApi('/');

function FeedSkeleton() {
  return (
    <div aria-hidden="true" className="grid divide-y divide-border-subtle">
      {Array.from({ length: 3 }, (_, index) => (
        <div className="grid animate-pulse gap-3 py-4 sm:grid-cols-[52px_minmax(0,1fr)]" key={index}>
          <span className="hidden h-[69px] w-[52px] rounded-sm bg-muted sm:block" />
          <span className="grid min-w-0 content-start gap-2">
            <span className="h-3 w-1/3 rounded-sm bg-muted" />
            <span className="h-4 w-2/3 rounded-sm bg-muted" />
            <span className="h-3 w-full rounded-sm bg-muted" />
            <span className="h-3 w-2/5 rounded-sm bg-muted" />
          </span>
        </div>
      ))}
    </div>
  );
}

export function UserActivityFeed() {
  const { t } = useI18n();
  const navigate = homeRoute.useNavigate();
  const { activity_comments_page: commentsPage = 1 } = homeRoute.useSearch();
  const [expandedActivityId, setExpandedActivityId] = useState<number | null>(null);
  const feedQuery = useQuery(communityQueries.feed({ page_size: 5, include_self: true, ordering: '-created_at' }));
  const feedItems = (feedQuery.data?.results ?? []).slice(0, 5);

  return (
    <section className="home-panel home-feed-panel">
      <div className="home-section-header">
        <h2>{t('home.feed')}</h2>
        <Link className="text-sm font-semibold text-[var(--ui-accent-text)]" to={routes.communityPosts}>
          {t('home.viewAll')}
        </Link>
      </div>

      <div className="home-feed-list">
        {feedItems.map((activity) => (
          <div className="grid gap-3" key={activity.id}>
            <CommunityContentCard
              actions={
                <CommunityTargetActions
                  inlineMiddleAction={
                    <Toggle
                      aria-label={
                        expandedActivityId === activity.id ? t('community.hideComments') : t('community.viewComments')
                      }
                      className="timeline-action-button"
                      pressed={expandedActivityId === activity.id}
                      variant="bare"
                      onPressedChange={() => {
                        setExpandedActivityId((current) => (current === activity.id ? null : activity.id));
                      }}
                    >
                      <MessageSquare className="size-4" />
                      {typeof activity.reply_count === 'number' ? <span>{activity.reply_count}</span> : null}
                    </Toggle>
                  }
                  presentation="inline"
                  reactionCount={typeof activity.reaction_count === 'number' ? activity.reaction_count : undefined}
                  reportLabel={t('community.reportActivity')}
                  targetId={activity.id}
                  targetType="activity"
                  viewerState={activity.viewer_state}
                />
              }
              author={
                activity.user?.id
                  ? {
                      href: routes.userProfile(activity.user.id),
                      name: activity.user.nickname || t('common.anonymous'),
                      avatar: activity.user.avatar,
                    }
                  : undefined
              }
              body={activityBody(activity, t('common.noContent'))}
              cover={activity.subject?.image_thumbnail || null}
              date={formatDate(activity.created_at)}
              href={activityTargetHref(activity, routes.home)}
              icon={<MessageSquare className="size-4" />}
              presentation="flat"
              subject={
                activity.subject?.id
                  ? {
                      href: routes.subject(activity.subject.id),
                      title:
                        activity.subject.display_title ||
                        activity.subject.title ||
                        activity.subject.title_cn ||
                        t('common.untitledSubject'),
                    }
                  : undefined
              }
              title={activityTitle(activity, t('common.untitled'))}
              typeLabel={activityTypeLabel(activity.activity_type, t)}
            />
            {expandedActivityId === activity.id ? (
              <div className="activity-comments-drawer">
                <CommunityCommentsSection
                  currentPage={commentsPage}
                  targetId={activity.id}
                  targetType="activity"
                  onPageChange={(page) =>
                    void navigate({ search: (current) => ({ ...current, activity_comments_page: page }) })
                  }
                />
              </div>
            ) : null}
          </div>
        ))}
        {feedQuery.isLoading ? <FeedSkeleton /> : null}
        {feedQuery.isError ? (
          <ErrorState title={t('home.feedErrorTitle')} description={t('home.feedErrorBody')} />
        ) : null}
        {!feedQuery.isLoading && !feedQuery.isError && feedItems.length === 0 ? (
          <EmptyState
            title={t('home.feedEmptyTitle')}
            description={t('home.feedEmptyBody')}
            action={
              <Button asChild size="sm" variant="secondary">
                <Link to={routes.communityPosts}>{t('nav.posts')}</Link>
              </Button>
            }
          />
        ) : null}
      </div>
    </section>
  );
}
