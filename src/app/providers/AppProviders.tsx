import type { ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/entities/session';
import { I18nProvider } from '@/shared/i18n';
import { ThemeProvider } from '@/shared/theme/ThemeProvider';
import { queryClient } from '@/shared/query/query-client';
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
