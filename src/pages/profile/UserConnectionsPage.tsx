import { formatDate } from '@/shared/lib/date';
import { useCallback } from 'react';
import { getRouteApi, Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Users } from 'lucide-react';
import { useAuth } from '@/entities/session';
import { communityQueries } from '@/entities/community';
import { useI18n } from '@/shared/i18n';
import { publicUserQueries } from '@/entities/user';
import type { FollowRelation } from '@/shared/api';
import { parseIntegerParam } from '@/shared/routing/search-params';
import { Avatar } from '@/shared/ui/Avatar';
import { Button } from '@/shared/ui/Button';
import { ListSurface, ResultsState, type ResultsStatus } from '@/shared/ui/DataView';
import { ErrorState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 24;
type UserConnectionsPageProps = {
  currentPage: number;
  mode: 'followers' | 'following';
  onPageChange: (page: number) => void;
  userIdParam: string;
};

const followersRoute = getRouteApi('/users/$userId/followers');
const followingRoute = getRouteApi('/users/$userId/following');

function ConnectionItem({ relation }: { relation: FollowRelation }) {
  const { t } = useI18n();
  const user = relation.user;

  return (
    <article
      className="border-b border-border-subtle px-3 py-3 transition-colors last:border-b-0 hover:bg-muted sm:px-4"
      data-slot="connection-row"
    >
      <div className="grid min-w-0 grid-cols-[40px_minmax(0,1fr)] items-center gap-3 sm:grid-cols-[44px_minmax(0,1fr)_auto]">
        <Link params={{ userId: String(user.id) }} to="/users/$userId">
          <Avatar
            alt={user.nickname || t('common.anonymous')}
            className="size-10 rounded-full bg-muted object-cover transition hover:ring-2 hover:ring-[var(--ui-accent-border)] sm:size-11"
            src={user.avatar}
          />
        </Link>
        <div className="min-w-0">
          <Link
            className="line-clamp-1 text-sm font-semibold text-[var(--ui-text)] transition hover:text-[var(--ui-accent-text)]"
            params={{ userId: String(user.id) }}
            to="/users/$userId"
          >
            {user.nickname || t('common.anonymous')}
          </Link>
          <p className="mt-1 text-xs text-[var(--ui-text-muted)]">
            {t('profile.followedAt')} {formatDate(relation.followed_at)}
          </p>
        </div>
        <Button asChild className="col-start-2 w-fit sm:col-auto" size="sm" type="button" variant="secondary">
          <Link params={{ userId: String(user.id) }} to="/users/$userId">
            {t('profile.openProfile')}
          </Link>
        </Button>
      </div>
    </article>
  );
}

function UserConnectionsPage({ currentPage, mode, onPageChange, userIdParam }: UserConnectionsPageProps) {
  const { t } = useI18n();
  const auth = useAuth();
  const userId = parseIntegerParam(userIdParam, { min: 1 }) ?? 0;
  const isValidUserId = userId > 0;
  const isSelf = auth.profile?.user_id === userId;
  const profileQuery = useQuery({ ...publicUserQueries.publicProfile(userId), enabled: isValidUserId });
  const myFollowersQuery = useQuery({
    ...communityQueries.myFollowers({ page: currentPage, page_size: pageSize }),
    enabled: isValidUserId && isSelf && auth.isAuthenticated && mode === 'followers',
  });
  const myFollowingQuery = useQuery({
    ...communityQueries.myFollowing({ page: currentPage, page_size: pageSize }),
    enabled: isValidUserId && isSelf && auth.isAuthenticated && mode === 'following',
  });
  const followersQuery = useQuery({
    ...communityQueries.userFollowers(userId, { page: currentPage, page_size: pageSize }),
    enabled: isValidUserId && (!isSelf || !auth.isAuthenticated) && mode === 'followers',
  });
  const followingQuery = useQuery({
    ...communityQueries.userFollowing(userId, { page: currentPage, page_size: pageSize }),
    enabled: isValidUserId && (!isSelf || !auth.isAuthenticated) && mode === 'following',
  });
  const listQuery =
    isSelf && auth.isAuthenticated
      ? mode === 'followers'
        ? myFollowersQuery
        : myFollowingQuery
      : mode === 'followers'
        ? followersQuery
        : followingQuery;
  const relations = listQuery.data?.results ?? [];
  const totalPages = Math.max(1, Math.ceil((listQuery.data?.count ?? 0) / pageSize));
  const title = mode === 'followers' ? t('profile.followersTitle') : t('profile.followingTitle');
  const emptyTitle = mode === 'followers' ? t('profile.noFollowersTitle') : t('profile.noFollowingTitle');
  const emptyBody = mode === 'followers' ? t('profile.noFollowersBody') : t('profile.noFollowingBody');
  const resultsStatus: ResultsStatus =
    profileQuery.isLoading || (listQuery.data === undefined && listQuery.isLoading)
      ? 'loading'
      : profileQuery.isError || (listQuery.data === undefined && listQuery.isError)
        ? 'error'
        : relations.length === 0
          ? 'empty'
          : 'ready';

  if (!isValidUserId) {
    return (
      <Page title={title} eyebrow={t('profile.title')}>
        <ErrorState title={t('profile.invalidTitle')} description={t('profile.invalidBody')} />
      </Page>
    );
  }

  return (
    <Page
      title={title}
      eyebrow={t('profile.title')}
      actions={
        <Button asChild type="button" variant="secondary">
          <Link params={{ userId: String(userId) }} to="/users/$userId">
            <ArrowLeft className="size-4" /> {t('profile.backToProfile')}
          </Link>
        </Button>
      }
    >
      <ResultsState
        emptyAction={<Users className="size-4 text-subtle-foreground" />}
        emptyDescription={emptyBody}
        emptyTitle={emptyTitle}
        errorDescription={t('profile.connectionsErrorBody')}
        errorTitle={t('profile.connectionsErrorTitle')}
        loadingTitle={t('profile.loadingConnections')}
        status={resultsStatus}
      >
        <>
          <ListSurface>
            {relations.map((relation) => (
              <ConnectionItem key={`${relation.user.id}-${relation.followed_at}`} relation={relation} />
            ))}
          </ListSurface>
          <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={onPageChange} />
        </>
      </ResultsState>
    </Page>
  );
}

export function FollowersPage() {
  const { userId } = followersRoute.useParams();
  const { page = 1 } = followersRoute.useSearch();
  const navigate = followersRoute.useNavigate();
  const onPageChange = useCallback(
    (nextPage: number) => void navigate({ search: (current) => ({ ...current, page: nextPage }) }),
    [navigate],
  );

  return <UserConnectionsPage currentPage={page} mode="followers" onPageChange={onPageChange} userIdParam={userId} />;
}

export function FollowingPage() {
  const { userId } = followingRoute.useParams();
  const { page = 1 } = followingRoute.useSearch();
  const navigate = followingRoute.useNavigate();
  const onPageChange = useCallback(
    (nextPage: number) => void navigate({ search: (current) => ({ ...current, page: nextPage }) }),
    [navigate],
  );

  return <UserConnectionsPage currentPage={page} mode="following" onPageChange={onPageChange} userIdParam={userId} />;
}
