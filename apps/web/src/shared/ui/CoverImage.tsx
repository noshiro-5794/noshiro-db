import { useState } from 'react';
import { cn } from '@/shared/lib/cn';
import { coverTone, firstGlyphOf } from '@/shared/lib/identity';

/**
 * Cover artwork with a graceful failure mode.
 *
 * Provider CDNs go down, rotate file names and are unreachable from some
 * regions. A missing URL already falls back, but a URL that fails to load left
 * an empty grey rectangle, so both cases now draw the work's initial on a
 * deterministic tone — nothing on the page ever looks broken or half-loaded.
 */
export function CoverImage({
  alt = '',
  className,
  label,
  seed,
  src,
}: {
  alt?: string;
  className?: string | undefined;
  /** Work title, used for the fallback glyph. */
  label?: string | null | undefined;
  /** Stable identity for the fallback tone; defaults to the label. */
  seed?: string | null | undefined;
  src: string | null | undefined;
}) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return <CoverFallback alt={alt} className={className} label={label} seed={seed ?? label} />;
  }

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
      src={src}
    />
  );
}

function CoverFallback({
  alt,
  className,
  label,
  seed,
}: {
  alt: string;
  className?: string | undefined;
  label?: string | null | undefined;
  seed?: string | null | undefined;
}) {
  const glyph = firstGlyphOf(label);

  return (
    <span
      aria-hidden={alt ? undefined : true}
      aria-label={alt || undefined}
      className={cn('grid place-items-center overflow-hidden', className)}
      data-slot="cover-fallback"
      role={alt ? 'img' : undefined}
      style={coverTone(seed)}
    >
      {glyph ? (
        <svg aria-hidden="true" className="size-full" preserveAspectRatio="xMidYMid meet" viewBox="0 0 100 150">
          <text
            dominantBaseline="central"
            fill="currentColor"
            fontSize="40"
            fontWeight="550"
            textAnchor="middle"
            x="50"
            y="76"
          >
            {glyph}
          </text>
        </svg>
      ) : null}
    </span>
  );
}
