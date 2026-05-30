import { AppRoutes } from '@/routes/AppRoutes';
import { AppShell } from './AppShell';

export function App() {
  return (
    <AppShell>
      <AppRoutes />
    </AppShell>
  );
}
