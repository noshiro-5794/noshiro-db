import type { ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/features/auth/AuthProvider';
import { I18nProvider } from '@/features/i18n/I18nProvider';
import { ThemeProvider } from '@/features/theme/ThemeProvider';
import { queryClient } from '@/lib/query/query-client';
import { Toaster } from '@/shared/ui/Toaster';

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <ThemeProvider>
          <AuthProvider>{children}</AuthProvider>
          <Toaster />
        </ThemeProvider>
      </I18nProvider>
    </QueryClientProvider>
  );
}
