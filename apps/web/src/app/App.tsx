import { Outlet, useRouterState } from '@tanstack/react-router';
import { AppErrorBoundary } from '@/shared/ui/AppErrorBoundary';
import { AppShell } from './shell/AppShell';

export function App() {
  const resetKey = useRouterState({ select: (state) => state.location.href });

  return (
    <AppShell>
      <AppErrorBoundary resetKey={resetKey}>
        <Outlet />
      </AppErrorBoundary>
    </AppShell>
  );
}
