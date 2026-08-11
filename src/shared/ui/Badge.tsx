import type { ComponentProps } from 'react';
import { cn } from '@/shared/lib/cn';

type BadgeVariant = 'default' | 'secondary' | 'accent' | 'danger' | 'success' | 'warning';

const variantClasses: Record<BadgeVariant, string> = {
  default: 'border-[var(--ui-action-primary)] bg-[var(--ui-action-primary)] text-[var(--ui-action-primary-text)]',
  secondary: 'border-[var(--ui-border)] bg-[var(--ui-bg-subtle)] text-[var(--ui-text-muted)]',
  accent:
    'border-[color-mix(in_srgb,var(--ui-accent)_24%,var(--ui-border))] bg-[var(--ui-accent-soft)] text-[var(--ui-accent-text)]',
  danger:
    'border-[color-mix(in_srgb,var(--ui-danger)_24%,var(--ui-border))] bg-[var(--ui-danger-soft)] text-[var(--ui-danger-text)]',
  success:
    'border-[color-mix(in_srgb,var(--ui-success)_24%,var(--ui-border))] bg-[var(--ui-success-soft)] text-[var(--ui-success-text)]',
  warning:
    'border-[color-mix(in_srgb,var(--ui-warning)_28%,var(--ui-border))] bg-[var(--ui-warning-soft)] text-[var(--ui-warning-text)]',
};

function Badge({ className, variant = 'secondary', ...props }: ComponentProps<'span'> & { variant?: BadgeVariant }) {
  return (
    <span
      className={cn(
        'inline-flex min-h-5 w-fit shrink-0 items-center gap-1 rounded-sm border px-1.5 py-0.5 text-[11px] font-medium leading-none [&_svg]:size-3 [&_svg]:shrink-0',
        variantClasses[variant],
        className,
      )}
      data-slot="badge"
      data-variant={variant}
      {...props}
    />
  );
}

export { Badge };
