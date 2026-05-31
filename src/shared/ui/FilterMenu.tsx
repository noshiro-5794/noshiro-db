import { Check, ChevronDown } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/shared/ui/DropdownMenu';

export type FilterMenuOption<TValue extends string> = {
  label: string;
  value: TValue;
};

type FilterMenuProps<TValue extends string> = {
  label: string;
  options: Array<FilterMenuOption<TValue>>;
  value: TValue;
  onChange: (value: TValue) => void;
};

export function FilterMenu<TValue extends string>({ label, options, value, onChange }: FilterMenuProps<TValue>) {
  const selectedOption = options.find((option) => option.value === value) ?? options[0];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button className="w-full justify-between px-3" type="button" variant="secondary">
          <span className="flex min-w-0 items-center gap-1.5">
            <span className="text-neutral-400 dark:text-neutral-500">{label}</span>
            <span className="truncate">{selectedOption?.label}</span>
          </span>
          <ChevronDown className="size-4 flex-shrink-0 text-neutral-400" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="min-w-[var(--radix-dropdown-menu-trigger-width)]">
        {options.map((option) => {
          const isSelected = option.value === value;

          return (
            <DropdownMenuItem
              className="justify-between gap-3"
              key={option.value || 'empty'}
              onSelect={() => onChange(option.value)}
            >
              <span>{option.label}</span>
              {isSelected ? <Check className="size-4 text-[var(--color-accent-strong)]" /> : null}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
