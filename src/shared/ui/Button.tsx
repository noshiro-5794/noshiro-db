import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-semibold outline-none transition disabled:pointer-events-none disabled:opacity-50 focus-visible:ring-4 focus-visible:ring-[var(--color-focus-ring)]',
  {
    variants: {
      variant: {
        default: 'border border-[color-mix(in_srgb,var(--color-text)_16%,var(--color-border))] bg-[var(--color-text)] text-[var(--color-bg)] shadow-sm hover:opacity-90',
        secondary:
          'border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] shadow-sm hover:border-[var(--color-accent-border)] hover:bg-[var(--color-surface-muted)]',
        ghost: 'text-[var(--color-text-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-text)]',
        accent: 'bg-[var(--color-accent)] text-[var(--color-accent-contrast)] hover:bg-[var(--color-accent-strong)]',
      },
      size: {
        default: 'h-10 px-4',
        sm: 'h-9 px-3',
        lg: 'h-11 px-5',
        icon: 'size-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

type ButtonProps = React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  };

function Button({ asChild = false, className, size, variant, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : 'button';
  return <Comp className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}

export { Button };
