import { useCallback } from 'react';
import { getRouteApi } from '@tanstack/react-router';
import { PublicUserContentBrowser, type PublicContentSearchKey } from '@/widgets/public-content';
import {
  validatePublicCollectionsSearch,
  validatePublicReviewsSearch,
  validatePublicSubjectsSearch,
} from '@/shared/routing/route-search';

const publicReviewsRoute = getRouteApi('/users/$userId/reviews');
const publicSubjectsRoute = getRouteApi('/users/$userId/entities');
const publicCollectionsRoute = getRouteApi('/users/$userId/collections');

export function PublicReviewsPage() {
  const { userId } = publicReviewsRoute.useParams();
  const search = publicReviewsRoute.useSearch();
  const navigate = publicReviewsRoute.useNavigate();
  const onSearchChange = useCallback(
    (key: PublicContentSearchKey, value: string, options?: { replace?: boolean }) => {
      void navigate({
        ...(options?.replace === undefined ? {} : { replace: options.replace }),
        search: (current) => ({
          ...current,
          ...validatePublicReviewsSearch({
            ...current,
            [key]: value || undefined,
            page: key === 'page' ? value : undefined,
          }),
        }),
      });
    },
    [navigate],
  );
  const onResetSearch = useCallback(() => {
    void navigate({ search: {} });
  }, [navigate]);

  return (
    <PublicUserContentBrowser
      mode="reviews"
      onResetSearch={onResetSearch}
      onSearchChange={onSearchChange}
      search={search}
      userIdParam={userId}
    />
  );
}

export function PublicSubjectsPage() {
  const { userId } = publicSubjectsRoute.useParams();
  const search = publicSubjectsRoute.useSearch();
  const navigate = publicSubjectsRoute.useNavigate();
  const onSearchChange = useCallback(
    (key: PublicContentSearchKey, value: string, options?: { replace?: boolean }) => {
      void navigate({
        ...(options?.replace === undefined ? {} : { replace: options.replace }),
        search: (current) => ({
          ...current,
          ...validatePublicSubjectsSearch({
            ...current,
            [key]: value || undefined,
            page: key === 'page' ? value : undefined,
          }),
        }),
      });
    },
    [navigate],
  );
  const onResetSearch = useCallback(() => {
    void navigate({ search: {} });
  }, [navigate]);

  return (
    <PublicUserContentBrowser
      mode="subjects"
      onResetSearch={onResetSearch}
      onSearchChange={onSearchChange}
      search={search}
      userIdParam={userId}
    />
  );
}

export function PublicCollectionsPage() {
  const { userId } = publicCollectionsRoute.useParams();
  const search = publicCollectionsRoute.useSearch();
  const navigate = publicCollectionsRoute.useNavigate();
  const onSearchChange = useCallback(
    (key: PublicContentSearchKey, value: string, options?: { replace?: boolean }) => {
      void navigate({
        ...(options?.replace === undefined ? {} : { replace: options.replace }),
        search: (current) => ({
          ...current,
          ...validatePublicCollectionsSearch({
            ...current,
            [key]: value || undefined,
            page: key === 'page' ? value : undefined,
          }),
        }),
      });
    },
    [navigate],
  );
  const onResetSearch = useCallback(() => {
    void navigate({ search: {} });
  }, [navigate]);

  return (
    <PublicUserContentBrowser
      mode="collections"
      onResetSearch={onResetSearch}
      onSearchChange={onSearchChange}
      search={search}
      userIdParam={userId}
    />
  );
}
