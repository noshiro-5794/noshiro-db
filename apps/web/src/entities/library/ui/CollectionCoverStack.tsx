import type { ComponentProps } from 'react';
import { cn } from '@/shared/lib/cn';

const layerPositionClasses = [
  'left-2 -rotate-[7deg]',
  'left-14 -rotate-2',
  'left-24 rotate-3',
  'left-[9.5rem] rotate-[8deg]',
] as const;

type CollectionCoverStackProps = Omit<ComponentProps<'div'>, 'children'> & {
  images: Array<string | null | undefined>;
};

export function CollectionCoverStack({ className, images, ...props }: CollectionCoverStackProps) {
  return (
    <div
      aria-hidden="true"
      className={cn('relative h-24 min-w-0 overflow-hidden rounded-md', className)}
      data-slot="collection-cover-stack"
      {...props}
    >
      {layerPositionClasses.map((positionClass, index) => {
        const image = images[index];
        return (
          <span
            className={cn(
              'absolute bottom-2 top-2 w-16 overflow-hidden rounded-sm border border-border bg-muted shadow-[var(--ui-shadow-control)]',
              positionClass,
            )}
            data-layer={index}
            data-slot="collection-cover-layer"
            key={index}
          >
            {image ? (
              <img
                alt=""
                className="size-full object-cover"
                decoding="async"
                loading="lazy"
                referrerPolicy="no-referrer"
                src={image}
              />
            ) : null}
          </span>
        );
      })}
    </div>
  );
}
