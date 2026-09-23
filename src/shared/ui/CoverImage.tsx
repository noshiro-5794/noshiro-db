import { useState } from 'react';
import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { cn } from '@/shared/lib/cn';

const fallbackCover = placeholderImagePaths.subjectCover;

/**
 * Cover artwork with a graceful failure mode.
 *
 * Provider CDNs go down, rotate file names and are unreachable from some
 * regions. A missing URL already falls back, but a URL that fails to load left
 * an empty grey rectangle, so the element now swaps to the placeholder too.
 */
export function CoverImage({
  alt = '',
  className,
  src,
}: {
  alt?: string;
  className?: string;
  src: string | null | undefined;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <img
      alt={alt}
      className={cn('bg-[var(--ui-bg-subtle)] object-cover', className)}
      decoding="async"
      loading="lazy"
      onError={() => {
        setFailed(true);
      }}
      referrerPolicy="no-referrer"
      src={failed || !src ? fallbackCover : src}
    />
  );
}
