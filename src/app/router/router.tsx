import {
  createRootRoute,
  createRoute,
  createRouter,
  lazyRouteComponent,
  type RouterHistory,
} from '@tanstack/react-router';
import type { ComponentType } from 'react';
import { App } from '@/app/App';
import { PageLoader } from '@/shared/ui/PageLoader';
import { RequireAuth } from '@/app/router/RequireAuth';

const AdminPage = lazyRouteComponent(() => import('@/pages/admin/AdminPage'), 'AdminPage');
const BookmarksPage = lazyRouteComponent(() => import('@/pages/community/BookmarksPage'), 'BookmarksPage');
const CalendarPage = lazyRouteComponent(() => import('@/pages/calendar/CalendarPage'), 'CalendarPage');
const CollectionsPage = lazyRouteComponent(() => import('@/pages/collections/CollectionsPage'), 'CollectionsPage');
const CommunityPostPage = lazyRouteComponent(() => import('@/pages/community/CommunityPostPage'), 'CommunityPostPage');
const CommunityPostsPage = lazyRouteComponent(
  () => import('@/pages/community/CommunityPostsPage'),
  'CommunityPostsPage',
);
const DocsPage = lazyRouteComponent(() => import('@/pages/docs/DocsPage'), 'DocsPage');
const HomePage = lazyRouteComponent(() => import('@/pages/home/HomePage'), 'HomePage');
const LibraryPage = lazyRouteComponent(() => import('@/pages/library/LibraryPage'), 'LibraryPage');
const LoginPage = lazyRouteComponent(() => import('@/pages/auth/LoginPage'), 'LoginPage');
const MePage = lazyRouteComponent(() => import('@/pages/profile/MePage'), 'MePage');
const NotFoundPage = lazyRouteComponent(() => import('@/pages/system/NotFoundPage'), 'NotFoundPage');
const NotificationsPage = lazyRouteComponent(() => import('@/pages/community/NotificationsPage'), 'NotificationsPage');
const PublicCollectionPage = lazyRouteComponent(
  () => import('@/pages/collections/PublicCollectionPage'),
  'PublicCollectionPage',
);
const PublicUserContentPage = lazyRouteComponent(
  () => import('@/pages/profile/PublicUserContentPage'),
  'PublicUserContentPage',
);
const PublicUserPage = lazyRouteComponent(() => import('@/pages/profile/PublicUserPage'), 'PublicUserPage');
const RegisterPage = lazyRouteComponent(() => import('@/pages/auth/RegisterPage'), 'RegisterPage');
const ResetPasswordPage = lazyRouteComponent(() => import('@/pages/auth/ResetPasswordPage'), 'ResetPasswordPage');
const ReviewEditorPage = lazyRouteComponent(() => import('@/pages/reviews/ReviewEditorPage'), 'ReviewEditorPage');
const ReviewsPage = lazyRouteComponent(() => import('@/pages/reviews/ReviewsPage'), 'ReviewsPage');
const ReviewViewerPage = lazyRouteComponent(() => import('@/pages/reviews/ReviewViewerPage'), 'ReviewViewerPage');
const SearchPage = lazyRouteComponent(() => import('@/pages/search/SearchPage'), 'SearchPage');
const SettingsPage = lazyRouteComponent(() => import('@/pages/profile/SettingsPage'), 'SettingsPage');
const SubjectGraphPage = lazyRouteComponent(() => import('@/pages/subjects/SubjectGraphPage'), 'SubjectGraphPage');
const SubjectPage = lazyRouteComponent(() => import('@/pages/subjects/SubjectPage'), 'SubjectPage');
const UserConnectionsPage = lazyRouteComponent(
  () => import('@/pages/profile/UserConnectionsPage'),
  'UserConnectionsPage',
);

function authenticated(Component: ComponentType, adminOnly = false) {
  return function AuthenticatedRoute() {
    return (
      <RequireAuth adminOnly={adminOnly}>
        <Component />
      </RequireAuth>
    );
  };
}

function withProps<Props extends object>(Component: ComponentType<Props>, props: Props) {
  return function RouteWithProps() {
    return <Component {...props} />;
  };
}

type AppRouteComponent = NonNullable<Parameters<typeof createRoute>[0]['component']>;

const rootRoute = createRootRoute({
  component: App,
  notFoundComponent: NotFoundPage,
});

function route<const Path extends string>(path: Path, component: AppRouteComponent) {
  return createRoute({
    component,
    getParentRoute: () => rootRoute,
    path,
  });
}

const routeTree = rootRoute.addChildren([
  route('/', HomePage),
  route('/login', LoginPage),
  route('/register', RegisterPage),
  route('/password/reset', ResetPasswordPage),
  route('/search', SearchPage),
  route('/calendar', CalendarPage),
  route('/docs', DocsPage),
  route('/docs/$slug', DocsPage),
  route('/community/posts', authenticated(CommunityPostsPage)),
  route('/community/posts/$postId', authenticated(CommunityPostPage)),
  route('/users/$userId', PublicUserPage),
  route('/users/$userId/followers', withProps(UserConnectionsPage, { mode: 'followers' })),
  route('/users/$userId/following', withProps(UserConnectionsPage, { mode: 'following' })),
  route('/users/$userId/reviews', withProps(PublicUserContentPage, { mode: 'reviews' })),
  route('/users/$userId/subjects', withProps(PublicUserContentPage, { mode: 'subjects' })),
  route('/users/$userId/collections', withProps(PublicUserContentPage, { mode: 'collections' })),
  route('/users/$userId/collections/$collectionId', PublicCollectionPage),
  route('/notifications', authenticated(NotificationsPage)),
  route('/bookmarks', authenticated(BookmarksPage)),
  route('/admin', authenticated(AdminPage, true)),
  route('/me', authenticated(MePage)),
  route('/settings', authenticated(SettingsPage)),
  route('/library', authenticated(LibraryPage)),
  route('/collections', authenticated(CollectionsPage)),
  route('/reviews', authenticated(ReviewsPage)),
  route('/reviews/new', authenticated(ReviewEditorPage)),
  route('/reviews/$reviewId/edit', authenticated(ReviewEditorPage)),
  route('/reviews/$reviewId', authenticated(ReviewViewerPage)),
  route('/subjects/$subjectId/graph', SubjectGraphPage),
  route('/subjects/$subjectId', SubjectPage),
]);

export function createAppRouter(history?: RouterHistory) {
  return createRouter({
    defaultPendingComponent: PageLoader,
    defaultPreload: 'intent',
    defaultPreloadStaleTime: 30_000,
    history,
    routeTree,
    scrollRestoration: true,
  });
}

export const router = createAppRouter();

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
