import { AppRoutes } from '@/routes/AppRoutes';
import { AppErrorBoundary } from '@/shared/ui/AppErrorBoundary';
import { AppShell } from './AppShell';

export function App() {
  return (
    <AppShell>
      <AppErrorBoundary>
        <AppRoutes />
      </AppErrorBoundary>
    </AppShell>
  );
}
