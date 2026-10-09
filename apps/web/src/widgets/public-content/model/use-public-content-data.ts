import { useQuery } from '@tanstack/react-query';
import { publicUserQueries } from '@/entities/user';
import type { PublicCollectionsSearch, PublicReviewsSearch, PublicSubjectsSearch } from '@/shared/routing/route-search';

const pageSize = 12;

export type PublicContentSelection =
  | { mode: 'reviews'; search: PublicReviewsSearch }
  | { mode: 'subjects'; search: PublicSubjectsSearch }
  | { mode: 'collections'; search: PublicCollectionsSearch };

export function usePublicContentData({
  enabled,
  keyword,
  selection,
  userId,
}: {
  enabled: boolean;
  keyword: string;
  selection: PublicContentSelection;
  userId: number;
}) {
  const { mode, search } = selection;
  const reviewSearch = mode === 'reviews' ? search : null;
  const subjectSearch = mode === 'subjects' ? search : null;
  const collectionSearch = mode === 'collections' ? search : null;
  const currentPage = search.page ?? 1;
  const reviewsQuery = useQuery({
    ...publicUserQueries.publicReviews(userId, {
      ...(keyword ? { keyword } : {}),
      ordering: reviewSearch?.ordering ?? '-created_at',
      page: currentPage,
      page_size: pageSize,
    }),
    enabled: enabled && mode === 'reviews',
  });
  const subjectsQuery = useQuery({
    ...publicUserQueries.publicSubjects(userId, {
      ...(keyword ? { keyword } : {}),
      ...(subjectSearch?.status ? { status: subjectSearch.status } : {}),
      ...(subjectSearch?.subject_type ? { subject_type: subjectSearch.subject_type } : {}),
      ordering: subjectSearch?.ordering ?? '-id',
      page: currentPage,
      page_size: pageSize,
    }),
    enabled: enabled && mode === 'subjects',
  });
  const collectionsQuery = useQuery({
    ...publicUserQueries.publicCollections(userId, {
      ...(keyword ? { keyword } : {}),
      ordering: collectionSearch?.ordering ?? '-id',
      page: currentPage,
      page_size: pageSize,
    }),
    enabled: enabled && mode === 'collections',
  });
  const activeQuery = mode === 'reviews' ? reviewsQuery : mode === 'subjects' ? subjectsQuery : collectionsQuery;

  return {
    activeQuery,
    collectionsQuery,
    currentPage,
    reviewsQuery,
    subjectsQuery,
    totalCount: activeQuery.data?.count ?? 0,
    totalPages: Math.max(1, Math.ceil((activeQuery.data?.count ?? 0) / pageSize)),
  };
}
