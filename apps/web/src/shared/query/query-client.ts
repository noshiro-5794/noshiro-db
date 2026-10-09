import { QueryClient } from '@tanstack/react-query';
import { ApiError } from '@/shared/api';

const maxQueryRetries = 2;

export function shouldRetryQuery(failureCount: number, error: unknown) {
  if (failureCount >= maxQueryRetries) {
    return false;
  }

  if (!(error instanceof ApiError)) {
    return true;
  }

  return error.status === 408 || error.status === 429 || error.status >= 500;
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: shouldRetryQuery,
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});
