import type { ComponentProps } from 'react';
import { cn } from '@/shared/lib/cn';

function Textarea({ className, ...props }: ComponentProps<'textarea'>) {
  return (
    <textarea
      className={cn(
        'min-h-24 w-full resize-y rounded-sm border border-control-border bg-elevated px-2.5 py-2 text-[13px] leading-6 text-foreground shadow-[var(--ui-shadow-control)] outline-none transition-[border-color,box-shadow,background-color] duration-[var(--ui-transition-fast)] placeholder:text-placeholder hover:border-[var(--ui-border-strong)] focus:border-ring focus:ring-2 focus:ring-[var(--ui-focus-halo)] aria-invalid:border-destructive aria-invalid:ring-2 aria-invalid:ring-[var(--ui-danger-soft)] disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-60',
        className,
      )}
      data-slot="textarea"
      {...props}
    />
  );
}

export { Textarea };
