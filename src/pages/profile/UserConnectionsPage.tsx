import { Link, useParams, useSearchParams } from '@/shared/routing/navigation';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Users } from 'lucide-react';
import { useAuth } from '@/entities/session';
import { communityQueries } from '@/entities/community';
import { useI18n } from '@/shared/i18n';
import { publicUserQueries } from '@/entities/user';
import type { FollowRelation } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 24;
const avatarPlaceholder = '/assets/placeholders/avatar.png';

type UserConnectionsPageProps = {
  mode: 'followers' | 'following';
};

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function ConnectionItem({ relation }: { relation: FollowRelation }) {
  const { t } = useI18n();
  const user = relation.user;

  return (
    <article className="community-list-item">
      <div className="grid min-w-0 grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-3">
        <Link to={routes.userProfile(user.id)}>
          <img
            className="size-11 rounded-full bg-neutral-100 object-cover transition hover:ring-2 hover:ring-[var(--color-accent-border)] dark:bg-neutral-900"
            src={user.avatar || avatarPlaceholder}
            alt=""
          />
        </Link>
        <div className="min-w-0">
          <Link
            className="line-clamp-1 text-sm font-semibold text-neutral-950 transition hover:text-[var(--color-accent-strong)] dark:text-white"
            to={routes.userProfile(user.id)}
          >
            {user.nickname || t('common.anonymous')}
          </Link>
          <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
            {t('profile.followedAt')} {formatDate(relation.followed_at)}
          </p>
        </div>
        <Button asChild size="sm" type="button" variant="secondary">
          <Link to={routes.userProfile(user.id)}>{t('profile.openProfile')}</Link>
        </Button>
      </div>
    </article>
  );
}

export function UserConnectionsPage({ mode }: UserConnectionsPageProps) {
  const { t } = useI18n();
  const auth = useAuth();
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const userId = Number(params.userId);
  const isValidUserId = Number.isFinite(userId) && userId > 0;
  const isSelf = auth.profile?.user_id ? Number(auth.profile.user_id) === userId : false;
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
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

  function goToPage(page: number) {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(page));
    setSearchParams(next);
  }

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
          <Link to={routes.userProfile(userId)}>
            <ArrowLeft className="size-4" /> {t('profile.backToProfile')}
          </Link>
        </Button>
      }
    >
      {profileQuery.isLoading || listQuery.isLoading ? <LoadingState title={t('profile.loadingConnections')} /> : null}
      {profileQuery.isError || listQuery.isError ? (
        <ErrorState title={t('profile.connectionsErrorTitle')} description={t('profile.connectionsErrorBody')} />
      ) : null}
      {!listQuery.isLoading && !listQuery.isError && relations.length === 0 ? (
        <EmptyState title={emptyTitle} description={emptyBody} action={<Users className="size-4 text-neutral-400" />} />
      ) : null}
      <div className="community-list">
        {relations.map((relation) => (
          <ConnectionItem key={`${relation.user.id}-${relation.followed_at}`} relation={relation} />
        ))}
      </div>
      <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
    </Page>
  );
}
