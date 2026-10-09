import type { ComponentProps } from 'react';
import { cn } from '@/shared/lib/cn';

type CardProps = ComponentProps<'div'> & {
  size?: 'default' | 'sm';
};

function Card({ className, size = 'default', ...props }: CardProps) {
  return (
    <div
      className={cn('group/card flex flex-col rounded-md border border-border bg-surface text-foreground', className)}
      data-size={size}
      data-slot="card"
      {...props}
    />
  );
}

function CardHeader({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'grid auto-rows-min items-start gap-1 px-4 pb-3 pt-4 group-data-[size=sm]/card:px-3 group-data-[size=sm]/card:pb-2.5 group-data-[size=sm]/card:pt-3',
        className,
      )}
      data-slot="card-header"
      {...props}
    />
  );
}

function CardTitle({ className, ...props }: ComponentProps<'h2'>) {
  return (
    <h2
      className={cn('text-sm font-semibold leading-5 text-foreground', className)}
      data-slot="card-title"
      {...props}
    />
  );
}

function CardContent({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn('px-4 pb-4 group-data-[size=sm]/card:px-3 group-data-[size=sm]/card:pb-3', className)}
      data-slot="card-content"
      {...props}
    />
  );
}

export { Card, CardContent, CardHeader, CardTitle };
