import type { ComponentProps } from 'react';
import { cn } from '@/shared/lib/cn';
import { Toggle } from '@/shared/ui/Toggle';

function FilterPanel({ className, ...props }: ComponentProps<'section'>) {
  return (
    <section
      className={cn('grid gap-3 border-b border-border-subtle pb-4', className)}
      data-slot="filter-panel"
      {...props}
    />
  );
}

function FilterPanelHeader({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn('flex items-center gap-2 text-sm font-semibold text-foreground', className)}
      data-slot="filter-panel-header"
      {...props}
    />
  );
}

type FilterPanelChoiceProps = Omit<ComponentProps<typeof Toggle>, 'variant'>;

function FilterPanelChoice({ className, ...props }: FilterPanelChoiceProps) {
  return (
    <Toggle
      className={cn(
        'flex items-center justify-between rounded-sm px-2.5 py-1.5 text-left text-[13px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground data-[pressed]:bg-[color-mix(in_srgb,var(--ui-accent-soft)_70%,var(--ui-bg-muted))] data-[pressed]:text-[var(--ui-accent-text)]',
        className,
      )}
      data-slot="filter-panel-choice"
      variant="bare"
      {...props}
    />
  );
}

type FilterTagProps = ComponentProps<'span'> & {
  active?: boolean;
};

function FilterTag({ active = false, className, ...props }: FilterTagProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center overflow-hidden rounded-sm border border-border bg-[color-mix(in_srgb,var(--ui-bg-surface)_84%,var(--ui-bg-subtle))] text-xs font-medium text-muted-foreground data-[active]:border-[var(--ui-accent-border)] data-[active]:bg-[color-mix(in_srgb,var(--ui-accent-soft)_70%,var(--ui-bg-surface))] data-[active]:text-[var(--ui-accent-text)]',
        className,
      )}
      data-active={active || undefined}
      data-slot="filter-tag"
      {...props}
    />
  );
}

export { FilterPanel, FilterPanelChoice, FilterPanelHeader, FilterTag };
