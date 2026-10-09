import { ChevronDown } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/shared/ui/DropdownMenu';

export type FilterMenuOption<TValue extends string> = {
  label: string;
  value: TValue;
};

type FilterMenuProps<TValue extends string> = {
  label: string;
  options: ReadonlyArray<FilterMenuOption<TValue>>;
  size?: 'default' | 'lg';
  value: TValue;
  onChange: (value: TValue) => void;
};

function isOptionValue<TValue extends string>(
  options: ReadonlyArray<FilterMenuOption<TValue>>,
  value: unknown,
): value is TValue {
  return typeof value === 'string' && options.some((option) => option.value === value);
}

export function FilterMenu<TValue extends string>({
  label,
  options,
  size = 'default',
  value,
  onChange,
}: FilterMenuProps<TValue>) {
  const selectedOption = options.find((option) => option.value === value) ?? options[0];
  const showSelectedLabel = selectedOption?.label && selectedOption.label !== label;
  const accessibleLabel = showSelectedLabel ? `${label}: ${selectedOption.label}` : label;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            aria-label={accessibleLabel}
            className="group w-full justify-between border-[var(--ui-control-border)] data-[popup-open]:border-[var(--ui-accent-border)] data-[popup-open]:bg-[var(--ui-bg-muted)]"
            size={size}
            type="button"
            variant="secondary"
          />
        }
      >
        <span className="flex min-w-0 items-center gap-1.5">
          {/* The value leads; the field name only shows while nothing is chosen. */}
          {showSelectedLabel ? (
            <>
              <span className="truncate text-[var(--ui-text)]">{selectedOption.label}</span>
              <span className="truncate text-[var(--ui-text-subtle)]">{label}</span>
            </>
          ) : (
            <span className="truncate text-[var(--ui-text-subtle)]">{label}</span>
          )}
        </span>
        <ChevronDown className="size-[var(--ui-control-glyph-sm)] flex-shrink-0 text-[var(--ui-text-subtle)] transition-transform duration-[var(--ui-transition-standard)] ease-[var(--ui-ease-standard)] group-data-[popup-open]:rotate-180" />
      </DropdownMenuTrigger>
      <DropdownMenuContent className="min-w-[var(--anchor-width)]">
        <DropdownMenuRadioGroup
          value={value}
          onValueChange={(nextValue) => {
            if (isOptionValue(options, nextValue)) onChange(nextValue);
          }}
        >
          {options.map((option) => (
            <DropdownMenuRadioItem closeOnClick key={option.value || 'empty'} value={option.value}>
              {option.label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
