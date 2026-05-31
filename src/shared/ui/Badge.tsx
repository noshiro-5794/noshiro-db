import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold', {
  variants: {
    variant: {
      default: 'bg-neutral-950 text-white dark:bg-white dark:text-neutral-950',
      secondary: 'bg-neutral-100 text-neutral-600 dark:bg-neutral-900 dark:text-neutral-300',
      accent: 'bg-[var(--color-accent-soft)] text-[var(--color-accent-strong)]',
    },
  },
  defaultVariants: {
    variant: 'secondary',
  },
});

function Badge({ className, variant, ...props }: React.ComponentProps<'span'> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant, className }))} {...props} />;
}

export { Badge };
