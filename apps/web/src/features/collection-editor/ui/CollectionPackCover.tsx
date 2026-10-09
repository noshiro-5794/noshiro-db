import { useQuery } from '@tanstack/react-query';
import { CollectionCoverStack, libraryQueries } from '@/entities/library';
import type { CollectionItem } from '@/shared/api';
import { useVisibleOnce } from '@/shared/lib/use-visible-once';

function subjectImage(item: CollectionItem) {
  return item.subject.images?.thumbnail || item.subject.image_thumbnail || item.subject.image || null;
}

export function CollectionPackCover({ collectionId, hasItems }: { collectionId: number; hasItems: boolean }) {
  const { isVisible, ref } = useVisibleOnce();
  const previewQuery = useQuery({
    ...libraryQueries.collectionItems(collectionId, { page: 1, page_size: 4 }),
    enabled: hasItems && isVisible,
  });
  const previewItems = previewQuery.data?.results ?? [];
  const images = previewItems.map(subjectImage);

  return <CollectionCoverStack images={images} ref={ref} />;
}
