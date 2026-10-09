import { cn } from '@/shared/lib/cn';

/** The field name of a filter, in the muted slot of its trigger. */
export const filterTriggerFieldClass = 'text-[var(--ui-text-subtle)]';

/** The chosen value, in the strong slot of the same trigger. */
export const filterTriggerValueClass = 'font-medium text-[var(--ui-text)]';

/**
 * Every filter trigger shares one anatomy: field name first, value second.
 * Leading with the value reads well while a filter is narrowed, but the unset
 * value is the word "All", and "All Type" reads as a category rather than as an
 * empty filter. The field name therefore leads, and the value appears only once
 * the filter narrows something.
 */
function FilterTriggerLabel({ className, label, value }: { className?: string; label: string; value: string | null }) {
  return (
    <span className={cn('flex min-w-0 items-baseline gap-1.5', className)} data-slot="filter-trigger-label">
      <span className={cn('truncate', filterTriggerFieldClass)}>{label}</span>
      {value === null ? null : (
        <span className={cn('truncate', filterTriggerValueClass)} data-slot="filter-trigger-value">
          {value}
        </span>
      )}
    </span>
  );
}

export { FilterTriggerLabel };
