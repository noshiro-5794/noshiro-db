import { useMemo, useState } from 'react';
import { Check, ChevronDown } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/shared/ui/DropdownMenu';

type FilterComboboxOption<TValue extends string> = {
  label: string;
  value: TValue;
};

type FilterComboboxProps<TValue extends string> = {
  allowCustomValue?: (value: string) => boolean;
  label: string;
  options: Array<FilterComboboxOption<TValue>>;
  placeholder?: string;
  value: TValue;
  onChange: (value: TValue) => void;
};

export function FilterCombobox<TValue extends string>({
  allowCustomValue,
  label,
  options,
  placeholder,
  value,
  onChange,
}: FilterComboboxProps<TValue>) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const selectedOption = options.find((option) => option.value === value) ?? options[0];
  const trimmedQuery = query.trim();

  const filteredOptions = useMemo(() => {
    if (!trimmedQuery) {
      return options;
    }
    return options.filter((option) => option.label.includes(trimmedQuery) || option.value.includes(trimmedQuery));
  }, [options, trimmedQuery]);

  const canUseCustomValue =
    Boolean(trimmedQuery) &&
    Boolean(allowCustomValue?.(trimmedQuery)) &&
    !options.some((option) => option.value === trimmedQuery);

  function commitValue(nextValue: string) {
    onChange(nextValue as TValue);
    setQuery('');
    setIsOpen(false);
  }

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button className="w-full justify-between px-3" type="button" variant="secondary">
          <span className="flex min-w-0 items-center gap-1.5">
            <span className="text-neutral-400 dark:text-neutral-500">{label}</span>
            <span className="truncate">{selectedOption?.label}</span>
          </span>
          <ChevronDown className="size-4 flex-shrink-0 text-neutral-400" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="min-w-[var(--radix-dropdown-menu-trigger-width)] p-1.5">
        <div className="p-1">
          <input
            autoFocus
            className="h-9 w-full rounded-lg border-0 bg-[var(--color-surface-muted)] px-3 text-sm text-[var(--color-text)] outline-none ring-1 ring-transparent transition placeholder:text-neutral-400 focus:bg-[var(--color-surface)] focus:ring-[var(--color-focus-ring)]"
            placeholder={placeholder}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              event.stopPropagation();
              if (event.key === 'Enter' && canUseCustomValue) {
                event.preventDefault();
                commitValue(trimmedQuery);
              }
            }}
          />
        </div>

        <div className="max-h-60 overflow-y-auto p-1">
          {canUseCustomValue ? (
            <DropdownMenuItem className="justify-between gap-3" onSelect={() => commitValue(trimmedQuery)}>
              <span>{trimmedQuery}</span>
              <span className="text-xs text-neutral-400">{label}</span>
            </DropdownMenuItem>
          ) : null}
          {filteredOptions.map((option) => {
            const isSelected = option.value === value;

            return (
              <DropdownMenuItem
                className="justify-between gap-3"
                key={option.value || 'empty'}
                onSelect={() => commitValue(option.value)}
              >
                <span>{option.label}</span>
                {isSelected ? <Check className="size-4 text-[var(--color-accent-strong)]" /> : null}
              </DropdownMenuItem>
            );
          })}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
