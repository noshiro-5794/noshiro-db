import * as React from 'react';
import { cn } from '@/lib/utils';

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      className={cn(
        'h-11 w-full rounded-xl border-0 bg-white px-4 text-sm shadow-sm outline-none ring-1 ring-neutral-200 transition placeholder:text-neutral-400 focus:ring-4 focus:ring-neutral-200 dark:bg-neutral-950 dark:ring-neutral-800 dark:focus:ring-neutral-800',
        className,
      )}
      type={type}
      {...props}
    />
  );
}

export { Input };
