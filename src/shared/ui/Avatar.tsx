import type { ComponentProps, ReactNode } from 'react';
import { Avatar as BaseAvatar } from '@base-ui/react/avatar';
import { UserRound } from 'lucide-react';
import { cn } from '@/shared/lib/cn';

type AvatarProps = Omit<ComponentProps<typeof BaseAvatar.Root>, 'children'> & {
  alt?: string;
  fallback?: ReactNode;
  imageClassName?: string;
  loading?: 'eager' | 'lazy';
  src?: string | null | undefined;
};

function Avatar({ alt = '', className, fallback, imageClassName, loading = 'lazy', src, ...props }: AvatarProps) {
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
        className="grid size-full place-items-center bg-muted text-subtle-foreground [&_svg]:size-[45%]"
        data-slot="avatar-fallback"
      >
        {fallback ?? <UserRound aria-hidden="true" />}
      </BaseAvatar.Fallback>
    </BaseAvatar.Root>
  );
}

export { Avatar };
