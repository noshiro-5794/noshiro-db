import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { PageLoader } from '@/shared/ui/PageLoader';
import { RequireAuth } from '@/shared/ui/RequireAuth';
import { routes } from './paths';

const CalendarPage = lazy(() => import('@/pages/CalendarPage').then((module) => ({ default: module.CalendarPage })));
const AdminPage = lazy(() => import('@/pages/AdminPage').then((module) => ({ default: module.AdminPage })));
const BookmarksPage = lazy(() => import('@/pages/BookmarksPage').then((module) => ({ default: module.BookmarksPage })));
const CommunityPostsPage = lazy(() => import('@/pages/CommunityPostsPage').then((module) => ({ default: module.CommunityPostsPage })));
const CommunityPostPage = lazy(() => import('@/pages/CommunityPostPage').then((module) => ({ default: module.CommunityPostPage })));
const CollectionsPage = lazy(() => import('@/pages/CollectionsPage').then((module) => ({ default: module.CollectionsPage })));
const DocsPage = lazy(() => import('@/pages/DocsPage').then((module) => ({ default: module.DocsPage })));
const HomePage = lazy(() => import('@/pages/HomePage').then((module) => ({ default: module.HomePage })));
const LibraryPage = lazy(() => import('@/pages/LibraryPage').then((module) => ({ default: module.LibraryPage })));
const LoginPage = lazy(() => import('@/pages/LoginPage').then((module) => ({ default: module.LoginPage })));
const MePage = lazy(() => import('@/pages/MePage').then((module) => ({ default: module.MePage })));
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage').then((module) => ({ default: module.NotFoundPage })));
const NotificationsPage = lazy(() => import('@/pages/NotificationsPage').then((module) => ({ default: module.NotificationsPage })));
const UserConnectionsPage = lazy(() => import('@/pages/UserConnectionsPage').then((module) => ({ default: module.UserConnectionsPage })));
const PublicUserContentPage = lazy(() => import('@/pages/PublicUserContentPage').then((module) => ({ default: module.PublicUserContentPage })));
const PublicCollectionPage = lazy(() => import('@/pages/PublicCollectionPage').then((module) => ({ default: module.PublicCollectionPage })));
const PublicUserPage = lazy(() => import('@/pages/PublicUserPage').then((module) => ({ default: module.PublicUserPage })));
const RegisterPage = lazy(() => import('@/pages/RegisterPage').then((module) => ({ default: module.RegisterPage })));
const ResetPasswordPage = lazy(() => import('@/pages/ResetPasswordPage').then((module) => ({ default: module.ResetPasswordPage })));
const ReviewEditorPage = lazy(() => import('@/pages/ReviewEditorPage').then((module) => ({ default: module.ReviewEditorPage })));
const ReviewViewerPage = lazy(() => import('@/pages/ReviewViewerPage').then((module) => ({ default: module.ReviewViewerPage })));
const ReviewsPage = lazy(() => import('@/pages/ReviewsPage').then((module) => ({ default: module.ReviewsPage })));
const SearchPage = lazy(() => import('@/pages/SearchPage').then((module) => ({ default: module.SearchPage })));
const SettingsPage = lazy(() => import('@/pages/SettingsPage').then((module) => ({ default: module.SettingsPage })));
const SubjectPage = lazy(() => import('@/pages/SubjectPage').then((module) => ({ default: module.SubjectPage })));
const SubjectGraphPage = lazy(() => import('@/pages/SubjectGraphPage').then((module) => ({ default: module.SubjectGraphPage })));

export function AppRoutes() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path={routes.home} element={<HomePage />} />
        <Route path={routes.login} element={<LoginPage />} />
        <Route path={routes.register} element={<RegisterPage />} />
        <Route path={routes.resetPassword} element={<ResetPasswordPage />} />
        <Route path={routes.search} element={<SearchPage />} />
        <Route path={routes.calendar} element={<CalendarPage />} />
        <Route path={routes.docsRoot} element={<DocsPage />} />
        <Route path={routes.docsPattern} element={<DocsPage />} />
        <Route path={routes.communityPosts} element={<RequireAuth><CommunityPostsPage /></RequireAuth>} />
        <Route path={routes.communityPostPattern} element={<RequireAuth><CommunityPostPage /></RequireAuth>} />
        <Route path={routes.userProfilePattern} element={<RequireAuth><PublicUserPage /></RequireAuth>} />
        <Route path={routes.userFollowersPattern} element={<RequireAuth><UserConnectionsPage mode="followers" /></RequireAuth>} />
        <Route path={routes.userFollowingPattern} element={<RequireAuth><UserConnectionsPage mode="following" /></RequireAuth>} />
        <Route path={routes.userReviewsPattern} element={<RequireAuth><PublicUserContentPage mode="reviews" /></RequireAuth>} />
        <Route path={routes.userSubjectsPattern} element={<RequireAuth><PublicUserContentPage mode="subjects" /></RequireAuth>} />
        <Route path={routes.userCollectionsPattern} element={<RequireAuth><PublicUserContentPage mode="collections" /></RequireAuth>} />
        <Route path={routes.userCollectionPattern} element={<RequireAuth><PublicCollectionPage /></RequireAuth>} />
        <Route path={routes.notifications} element={<RequireAuth><NotificationsPage /></RequireAuth>} />
        <Route path={routes.bookmarks} element={<RequireAuth><BookmarksPage /></RequireAuth>} />
        <Route path={routes.admin} element={<RequireAuth adminOnly><AdminPage /></RequireAuth>} />
        <Route path={routes.me} element={<RequireAuth><MePage /></RequireAuth>} />
        <Route path={routes.settings} element={<RequireAuth><SettingsPage /></RequireAuth>} />
        <Route path={routes.library} element={<RequireAuth><LibraryPage /></RequireAuth>} />
        <Route path={routes.collections} element={<RequireAuth><CollectionsPage /></RequireAuth>} />
        <Route path={routes.reviews} element={<RequireAuth><ReviewsPage /></RequireAuth>} />
        <Route path={routes.reviewNew} element={<RequireAuth><ReviewEditorPage /></RequireAuth>} />
        <Route path={routes.reviewEditPattern} element={<RequireAuth><ReviewEditorPage /></RequireAuth>} />
        <Route path={routes.reviewPattern} element={<RequireAuth><ReviewViewerPage /></RequireAuth>} />
        <Route path={routes.subjectGraphPattern} element={<SubjectGraphPage />} />
        <Route path={routes.subjectPattern} element={<SubjectPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}
