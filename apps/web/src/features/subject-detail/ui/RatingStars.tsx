import { Star } from 'lucide-react';
import { Button } from '@/shared/ui/Button';

export function StarRatingControl({
  clearLabel,
  disabled,
  label,
  value,
  onChange,
}: {
  clearLabel: string;
  disabled?: boolean;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const numericValue = Number(value || 0);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div
        aria-label={label}
        className="inline-flex rounded-sm border border-control-border bg-elevated p-0.5 shadow-[var(--ui-shadow-control)]"
        role="group"
      >
        {[1, 2, 3, 4, 5].map((ratingValue) => {
          const active = numericValue >= ratingValue;
          return (
            <Button
              aria-label={`${label} ${ratingValue} / 5`}
              aria-pressed={numericValue === ratingValue}
              className={`grid size-8 place-items-center rounded-sm transition-colors ${
                active
                  ? 'text-[var(--ui-accent-text)]'
                  : 'text-subtle-foreground hover:bg-muted hover:text-muted-foreground'
              }`}
              disabled={disabled}
              key={ratingValue}
              type="button"
              variant="unstyled"
              onClick={() => {
                onChange(String(ratingValue));
              }}
            >
              <Star className="size-4" fill={active ? 'currentColor' : 'none'} />
            </Button>
          );
        })}
      </div>
      <Button
        disabled={disabled || !value}
        size="xs"
        type="button"
        variant="ghost"
        onClick={() => {
          onChange('');
        }}
      >
        {clearLabel}
      </Button>
    </div>
  );
}

export function StarRatingDisplay({ value, emptyLabel }: { value?: number | null; emptyLabel: string }) {
  if (!value) return <span className="text-sm font-semibold text-[var(--ui-text)]">{emptyLabel}</span>;

  return (
    <span className="inline-flex items-center gap-0.5 text-[var(--ui-accent-text)]">
      {[1, 2, 3, 4, 5].map((ratingValue) => (
        <Star className="size-3.5" fill={value >= ratingValue ? 'currentColor' : 'none'} key={ratingValue} />
      ))}
    </span>
  );
}
