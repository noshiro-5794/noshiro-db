import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { PageLoader } from '@/shared/ui/PageLoader';
import { RequireAuth } from '@/shared/ui/RequireAuth';
import { routes } from './paths';

const CalendarPage = lazy(() => import('@/pages/CalendarPage').then((module) => ({ default: module.CalendarPage })));
const CollectionsPage = lazy(() => import('@/pages/CollectionsPage').then((module) => ({ default: module.CollectionsPage })));
const DevApiPage = lazy(() => import('@/pages/DevApiPage').then((module) => ({ default: module.DevApiPage })));
const DocsPage = lazy(() => import('@/pages/DocsPage').then((module) => ({ default: module.DocsPage })));
const HomePage = lazy(() => import('@/pages/HomePage').then((module) => ({ default: module.HomePage })));
const LibraryPage = lazy(() => import('@/pages/LibraryPage').then((module) => ({ default: module.LibraryPage })));
const LoginPage = lazy(() => import('@/pages/LoginPage').then((module) => ({ default: module.LoginPage })));
const MePage = lazy(() => import('@/pages/MePage').then((module) => ({ default: module.MePage })));
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage').then((module) => ({ default: module.NotFoundPage })));
const RegisterPage = lazy(() => import('@/pages/RegisterPage').then((module) => ({ default: module.RegisterPage })));
const ReviewsPage = lazy(() => import('@/pages/ReviewsPage').then((module) => ({ default: module.ReviewsPage })));
const SearchPage = lazy(() => import('@/pages/SearchPage').then((module) => ({ default: module.SearchPage })));
const SubjectPage = lazy(() => import('@/pages/SubjectPage').then((module) => ({ default: module.SubjectPage })));

export function AppRoutes() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path={routes.home} element={<HomePage />} />
        <Route path={routes.login} element={<LoginPage />} />
        <Route path={routes.register} element={<RegisterPage />} />
        <Route path={routes.search} element={<SearchPage />} />
        <Route path={routes.calendar} element={<CalendarPage />} />
        <Route path={routes.docsRoot} element={<DocsPage />} />
        <Route path={routes.docsPattern} element={<DocsPage />} />
        <Route path={routes.me} element={<RequireAuth><MePage /></RequireAuth>} />
        <Route path={routes.library} element={<RequireAuth><LibraryPage /></RequireAuth>} />
        <Route path={routes.collections} element={<RequireAuth><CollectionsPage /></RequireAuth>} />
        <Route path={routes.reviews} element={<RequireAuth><ReviewsPage /></RequireAuth>} />
        <Route path={routes.devApi} element={<RequireAuth><DevApiPage /></RequireAuth>} />
        <Route path={routes.subjectPattern} element={<SubjectPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}
