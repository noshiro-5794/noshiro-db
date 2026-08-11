import {
  createRootRoute,
  createRoute,
  createRouter,
  lazyRouteComponent,
  notFound,
  type RouterHistory,
} from '@tanstack/react-router';
import type { ComponentType } from 'react';
import { App } from '@/app/App';
import {
  validateBookmarksSearch,
  validateCollectionsSearch,
  validateCommunityPostsSearch,
  validateEmptySearch,
  validateLibrarySearch,
  validateMeSearch,
  validatePaginationSearch,
  validatePublicCollectionsSearch,
  validatePublicReviewsSearch,
  validatePublicSubjectsSearch,
  validateReviewEditorSearch,
  validateReviewsSearch,
  validateRootSearch,
  validateSearchPageSearch,
} from '@/shared/routing/route-search';
import { PageLoader } from '@/shared/ui/PageLoader';
import { RouteErrorState } from '@/shared/ui/RouteErrorState';
import { RequireAuth } from '@/app/router/RequireAuth';
import { parseIntegerParam } from '@/shared/routing/search-params';
import { parseUuid } from '@/shared/lib/validation';

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
const DocsIndexPage = lazyRouteComponent(() => import('@/pages/docs/DocsPage'), 'DocsIndexPage');
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
const PublicCollectionsPage = lazyRouteComponent(
  () => import('@/pages/profile/PublicUserContentPage'),
  'PublicCollectionsPage',
);
const PublicReviewsPage = lazyRouteComponent(
  () => import('@/pages/profile/PublicUserContentPage'),
  'PublicReviewsPage',
);
const PublicSubjectsPage = lazyRouteComponent(
  () => import('@/pages/profile/PublicUserContentPage'),
  'PublicSubjectsPage',
);
const PublicUserPage = lazyRouteComponent(() => import('@/pages/profile/PublicUserPage'), 'PublicUserPage');
const RegisterPage = lazyRouteComponent(() => import('@/pages/auth/RegisterPage'), 'RegisterPage');
const ResetPasswordPage = lazyRouteComponent(() => import('@/pages/auth/ResetPasswordPage'), 'ResetPasswordPage');
const NewReviewPage = lazyRouteComponent(() => import('@/pages/reviews/ReviewEditorPage'), 'NewReviewPage');
const EditReviewPage = lazyRouteComponent(() => import('@/pages/reviews/ReviewEditorPage'), 'EditReviewPage');
const ReviewsPage = lazyRouteComponent(() => import('@/pages/reviews/ReviewsPage'), 'ReviewsPage');
const ReviewViewerPage = lazyRouteComponent(() => import('@/pages/reviews/ReviewViewerPage'), 'ReviewViewerPage');
const SearchPage = lazyRouteComponent(() => import('@/pages/search/SearchPage'), 'SearchPage');
const SettingsPage = lazyRouteComponent(() => import('@/pages/profile/SettingsPage'), 'SettingsPage');
const SubjectGraphPage = lazyRouteComponent(() => import('@/pages/subjects/SubjectGraphPage'), 'SubjectGraphPage');
const SubjectPage = lazyRouteComponent(() => import('@/pages/subjects/SubjectPage'), 'SubjectPage');
const FollowersPage = lazyRouteComponent(() => import('@/pages/profile/UserConnectionsPage'), 'FollowersPage');
const FollowingPage = lazyRouteComponent(() => import('@/pages/profile/UserConnectionsPage'), 'FollowingPage');

function authenticated(Component: ComponentType, adminOnly = false) {
  return function AuthenticatedRoute() {
    return (
      <RequireAuth adminOnly={adminOnly}>
        <Component />
      </RequireAuth>
    );
  };
}

type AppRouteComponent = NonNullable<Parameters<typeof createRoute>[0]['component']>;
type RouteParamsValidator = (params: Record<string, string>) => void;

const rootRoute = createRootRoute({
  component: App,
  notFoundComponent: NotFoundPage,
  validateSearch: validateRootSearch,
});

function route<const Path extends string, SearchSchema>(
  path: Path,
  component: AppRouteComponent,
  validateSearch: (search: Record<string, unknown>) => SearchSchema,
  validateParams: RouteParamsValidator = () => undefined,
) {
  return createRoute({
    beforeLoad: ({ params }) => {
      validateParams(params);
    },
    component,
    getParentRoute: () => rootRoute,
    path,
    validateSearch,
  });
}

function requirePositiveIntegerParams(...keys: string[]): RouteParamsValidator {
  return (params) => {
    if (keys.some((key) => parseIntegerParam(params[key], { min: 1 }) === null)) notFound({ throw: true });
  };
}

const requirePostId = requirePositiveIntegerParams('postId');
const requireReviewId = requirePositiveIntegerParams('reviewId');
const requireUserId = requirePositiveIntegerParams('userId');
const requireUserCollectionIds = requirePositiveIntegerParams('userId', 'collectionId');
const requireSubjectId: RouteParamsValidator = (params) => {
  if (!parseUuid(params['subjectId'])) notFound({ throw: true });
};

const routeTree = rootRoute.addChildren([
  route('/', HomePage, validateEmptySearch),
  route('/login', LoginPage, validateEmptySearch),
  route('/register', RegisterPage, validateEmptySearch),
  route('/password/reset', ResetPasswordPage, validateEmptySearch),
  route('/search', SearchPage, validateSearchPageSearch),
  route('/calendar', CalendarPage, validateEmptySearch),
  route('/docs', DocsIndexPage, validateEmptySearch),
  route('/docs/$slug', DocsPage, validateEmptySearch),
  route('/community/posts', authenticated(CommunityPostsPage), validateCommunityPostsSearch),
  // Public post details can be shared directly. Mutation controls remain gated in the page and feature layers.
  route('/community/posts/$postId', CommunityPostPage, validateEmptySearch, requirePostId),
  route('/users/$userId', PublicUserPage, validateEmptySearch, requireUserId),
  route('/users/$userId/followers', FollowersPage, validatePaginationSearch, requireUserId),
  route('/users/$userId/following', FollowingPage, validatePaginationSearch, requireUserId),
  route('/users/$userId/reviews', PublicReviewsPage, validatePublicReviewsSearch, requireUserId),
  route('/users/$userId/subjects', PublicSubjectsPage, validatePublicSubjectsSearch, requireUserId),
  route('/users/$userId/collections', PublicCollectionsPage, validatePublicCollectionsSearch, requireUserId),
  route(
    '/users/$userId/collections/$collectionId',
    PublicCollectionPage,
    validatePaginationSearch,
    requireUserCollectionIds,
  ),
  route('/notifications', authenticated(NotificationsPage), validatePaginationSearch),
  route('/bookmarks', authenticated(BookmarksPage), validateBookmarksSearch),
  route('/admin', authenticated(AdminPage, true), validateEmptySearch),
  route('/me', authenticated(MePage), validateMeSearch),
  route('/settings', authenticated(SettingsPage), validateEmptySearch),
  route('/library', authenticated(LibraryPage), validateLibrarySearch),
  route('/collections', authenticated(CollectionsPage), validateCollectionsSearch),
  route('/reviews', authenticated(ReviewsPage), validateReviewsSearch),
  route('/reviews/new', authenticated(NewReviewPage), validateReviewEditorSearch),
  route('/reviews/$reviewId/edit', authenticated(EditReviewPage), validateEmptySearch, requireReviewId),
  // Public reviews are readable without a session; private reviews still resolve through the authenticated API.
  route('/reviews/$reviewId', ReviewViewerPage, validateEmptySearch, requireReviewId),
  route('/subjects/$subjectId/graph', SubjectGraphPage, validateEmptySearch, requireSubjectId),
  route('/subjects/$subjectId', SubjectPage, validateEmptySearch, requireSubjectId),
]);

export function createAppRouter(history?: RouterHistory) {
  return createRouter({
    defaultErrorComponent: RouteErrorState,
    defaultOnCatch: (error, errorInfo) => {
      console.error('Unhandled route error', error, errorInfo);
    },
    defaultPendingComponent: PageLoader,
    defaultPreload: 'intent',
    defaultPreloadStaleTime: 30_000,
    ...(history === undefined ? {} : { history }),
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
