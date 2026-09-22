import type { ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';

export function SourceDot({ className, provider }: { className?: string; provider: string }) {
  return (
    <span
      aria-hidden
      className={cn('calendar-dot inline-block size-2 shrink-0 rounded-full', className)}
      data-cal-source={provider}
    />
  );
}

export function IconButton({
  children,
  className,
  label,
  onClick,
}: {
  children: ReactNode;
  className?: string | undefined;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      aria-label={label}
      className={cn(
        'grid size-8 shrink-0 place-items-center rounded-full text-[var(--ui-text-muted)] transition-colors',
        'hover:bg-[var(--ui-bg-subtle)] hover:text-[var(--ui-text)]',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--ui-focus)]',
        className,
      )}
      onClick={onClick}
      title={label}
      type="button"
    >
      {children}
    </button>
  );
}

type SegmentedOption<Value extends string> = {
  value: Value;
  label: string;
  count?: number;
};

export function SegmentedControl<Value extends string>({
  ariaLabel,
  className,
  onChange,
  options,
  value,
}: {
  ariaLabel: string;
  className?: string;
  onChange: (value: Value) => void;
  options: SegmentedOption<Value>[];
  value: Value;
}) {
  return (
    <div
      aria-label={ariaLabel}
      className={cn(
        'inline-flex items-center gap-0.5 rounded-full border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] p-0.5',
        className,
      )}
      role="tablist"
    >
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            aria-selected={active}
            className={cn(
              'rounded-full px-3 py-1 text-xs font-medium transition-colors',
              active
                ? 'bg-[var(--ui-accent)] text-[var(--ui-accent-contrast)]'
                : 'text-[var(--ui-text-muted)] hover:text-[var(--ui-text)]',
            )}
            key={option.value}
            onClick={() => {
              onChange(option.value);
            }}
            role="tab"
            type="button"
          >
            {option.label}
            {option.count === undefined ? null : <span className="ml-1 tabular-nums opacity-70">{option.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

export function Panel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        'overflow-hidden rounded-[var(--ui-radius-frame)] border border-[var(--ui-border)] bg-[var(--ui-bg-surface)]',
        className,
      )}
    >
      {children}
    </div>
  );
}
