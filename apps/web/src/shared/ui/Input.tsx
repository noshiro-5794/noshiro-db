import type { ComponentProps } from 'react';
import { Input as BaseInput } from '@base-ui/react/input';
import { cn } from '@/shared/lib/cn';

function Input({ className, type, ...props }: ComponentProps<typeof BaseInput>) {
  return (
    <BaseInput
      className={cn(
        'h-[var(--ui-control-height)] w-full rounded-sm border border-control-border bg-elevated px-2.5 text-[13px] text-foreground shadow-[var(--ui-shadow-control)] outline-none transition-[border-color,box-shadow,background-color] duration-[var(--ui-transition-fast)] placeholder:text-placeholder hover:border-[var(--ui-border-strong)] focus:border-ring focus:ring-2 focus:ring-[var(--ui-focus-halo)] aria-invalid:border-destructive aria-invalid:ring-2 aria-invalid:ring-[var(--ui-danger-soft)] disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-60',
        className,
      )}
      data-slot="input"
      type={type}
      {...props}
    />
  );
}

export { Input };
