import { Outlet } from '@tanstack/react-router';
import { AppErrorBoundary } from '@/shared/ui/AppErrorBoundary';
import { AppShell } from './shell/AppShell';

export function App() {
  return (
    <AppShell>
      <AppErrorBoundary>
        <Outlet />
      </AppErrorBoundary>
    </AppShell>
  );
}
