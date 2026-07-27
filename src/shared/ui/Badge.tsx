import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/shared/lib/cn';

const badgeVariants = cva('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold', {
  variants: {
    variant: {
      default: 'bg-[var(--color-text)] text-[var(--color-bg)]',
      secondary: 'bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]',
      accent: 'bg-[var(--color-accent-soft)] text-[var(--color-accent-strong)]',
      danger: 'bg-red-50 text-red-600 dark:bg-red-950/30 dark:text-red-300',
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
