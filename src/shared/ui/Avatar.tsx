import type { ComponentProps, ReactNode } from 'react';
import { Avatar as BaseAvatar } from '@base-ui/react/avatar';
import { UserRound } from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import { avatarTone, initialsOf } from '@/shared/lib/identity';

type AvatarProps = Omit<ComponentProps<typeof BaseAvatar.Root>, 'children'> & {
  alt?: string;
  fallback?: ReactNode;
  imageClassName?: string;
  loading?: 'eager' | 'lazy';
  /** Name behind the initials shown when there is no picture. */
  name?: string | null | undefined;
  /** Stable identity for the fallback tone; defaults to the name. */
  seed?: string | null | undefined;
  src?: string | null | undefined;
};

function Avatar({
  alt = '',
  className,
  fallback,
  imageClassName,
  loading = 'lazy',
  name,
  seed,
  src,
  ...props
}: AvatarProps) {
  const initials = initialsOf(name);

  return (
    <BaseAvatar.Root
      aria-label={alt || undefined}
      className={cn(
        'relative inline-flex size-10 shrink-0 overflow-hidden rounded-full bg-muted align-middle text-subtle-foreground ring-1 ring-inset ring-border',
        className,
      )}
      data-slot="avatar"
      role={alt ? 'img' : undefined}
      {...props}
    >
      {src ? (
        <BaseAvatar.Image
          alt=""
          className={cn('size-full object-cover', imageClassName)}
          data-slot="avatar-image"
          decoding="async"
          loading={loading}
          referrerPolicy="no-referrer"
          src={src}
        />
      ) : null}
      <BaseAvatar.Fallback
        aria-hidden={alt ? true : undefined}
        className="grid size-full place-items-center"
        data-slot="avatar-fallback"
        style={avatarTone(seed ?? name)}
      >
        {fallback ??
          (initials ? <AvatarInitials value={initials} /> : <UserRound aria-hidden="true" className="size-[45%]" />)}
      </BaseAvatar.Fallback>
    </BaseAvatar.Root>
  );
}

/**
 * Initials are drawn in SVG so they scale with any avatar size, from the 16px
 * chip in a comment row to the 96px profile header.
 */
function AvatarInitials({ value }: { value: string }) {
  return (
    <svg aria-hidden="true" className="size-full" viewBox="0 0 40 40">
      <text
        dominantBaseline="central"
        fill="currentColor"
        fontSize={value.length > 1 ? '15' : '18'}
        fontWeight="550"
        textAnchor="middle"
        x="20"
        y="20.5"
      >
        {value}
      </text>
    </svg>
  );
}

export { Avatar };
