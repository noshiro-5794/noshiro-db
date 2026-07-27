import * as React from 'react';
import { cn } from '@/shared/lib/cn';

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      className={cn(
        'h-11 w-full rounded-xl border-0 bg-[var(--color-surface)] px-4 text-sm text-[var(--color-text)] shadow-sm outline-none ring-1 ring-[var(--color-border)] transition placeholder:text-neutral-400 focus:ring-4 focus:ring-[var(--color-focus-ring)]',
        className,
      )}
      type={type}
      {...props}
    />
  );
}

export { Input };
