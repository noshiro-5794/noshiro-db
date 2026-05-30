import { Navigate, Route, Routes } from 'react-router-dom';
import { CalendarPage } from '@/pages/CalendarPage';
import { HomePage } from '@/pages/HomePage';
import { MePage } from '@/pages/MePage';
import { SearchPage } from '@/pages/SearchPage';
import { SubjectPage } from '@/pages/SubjectPage';
import { DevApiPage } from '@/pages/DevApiPage';
import { routes } from './paths';

export function AppRoutes() {
  return (
    <Routes>
      <Route path={routes.home} element={<HomePage />} />
      <Route path={routes.search} element={<SearchPage />} />
      <Route path={routes.calendar} element={<CalendarPage />} />
      <Route path={routes.me} element={<MePage />} />
      <Route path={routes.devApi} element={<DevApiPage />} />
      <Route path={routes.subjectPattern} element={<SubjectPage />} />
      <Route path="*" element={<Navigate to={routes.home} replace />} />
    </Routes>
  );
}
