import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
  ComboboxTrigger,
} from '@/shared/ui/Combobox';
import { filterTriggerFieldClass, filterTriggerValueClass } from '@/shared/ui/FilterTrigger';
import { InputGroup, InputGroupAddon } from '@/shared/ui/InputGroup';

type FilterComboboxOption<TValue extends string> = {
  label: string;
  value: TValue;
};

type FilterComboboxProps<TValue extends string> = {
  createValue?: (query: string) => TValue | null;
  /** Option value that means the filter is not narrowing anything. Defaults to the empty string. */
  emptyValue?: string;
  label: string;
  options: Array<FilterComboboxOption<TValue>>;
  placeholder?: string;
  size?: 'default' | 'lg';
  value: TValue;
  onChange: (value: TValue) => void;
};

export function FilterCombobox<TValue extends string>({
  createValue,
  emptyValue = '',
  label,
  options,
  placeholder,
  size = 'default',
  value,
  onChange,
}: FilterComboboxProps<TValue>) {
  const { t } = useI18n();
  const narrowed = value !== emptyValue;
  const selectedOption = useMemo(
    () => (narrowed ? (options.find((option) => option.value === value) ?? { label: value, value }) : null),
    [narrowed, options, value],
  );
  // An unset filter leaves the value slot empty, so the field name is the only label the trigger shows.
  const selectedLabel = selectedOption?.label ?? '';
  const [inputValue, setInputValue] = useState(selectedLabel);
  const [isOpen, setIsOpen] = useState(false);
  const trimmedQuery = inputValue.trim();

  useEffect(() => {
    setInputValue(selectedLabel);
  }, [selectedLabel]);

  const optionsWithSelectedValue = useMemo(
    () =>
      selectedOption && !options.some((option) => option.value === selectedOption.value)
        ? [selectedOption, ...options]
        : options,
    [options, selectedOption],
  );

  const customOption = useMemo(() => {
    const customValue = trimmedQuery ? createValue?.(trimmedQuery) : null;
    if (
      customValue === null ||
      customValue === undefined ||
      optionsWithSelectedValue.some((option) => option.value === customValue)
    ) {
      return null;
    }
    return { label: trimmedQuery, value: customValue };
  }, [createValue, optionsWithSelectedValue, trimmedQuery]);

  const displayOptions = customOption ? [customOption, ...optionsWithSelectedValue] : optionsWithSelectedValue;

  return (
    <Combobox
      autoHighlight
      inputValue={inputValue}
      isItemEqualToValue={(option, selectedValue) => option.value === selectedValue.value}
      itemToStringLabel={(option) => option.label}
      items={displayOptions}
      open={isOpen}
      value={selectedOption}
      onInputValueChange={setInputValue}
      onOpenChange={(open) => {
        setIsOpen(open);
        if (!open) setInputValue(selectedLabel);
      }}
      onValueChange={(option) => {
        if (!option) return;
        onChange(option.value);
        setInputValue(option.label);
      }}
    >
      <InputGroup size={size}>
        <InputGroupAddon className={cn('shrink-0', filterTriggerFieldClass)}>{label}</InputGroupAddon>
        <ComboboxInput
          aria-label={label}
          className={cn('px-[var(--ui-control-gap)]', filterTriggerValueClass)}
          placeholder={placeholder}
          onFocus={(event) => {
            event.currentTarget.select();
          }}
        />
        <InputGroupAddon className="pl-0 pr-0.5">
          <ComboboxTrigger aria-label={label} />
        </InputGroupAddon>
      </InputGroup>
      <ComboboxContent>
        <ComboboxList>
          {(option: FilterComboboxOption<TValue>) => (
            <ComboboxItem key={option.value || 'empty'} value={option}>
              {option.label}
            </ComboboxItem>
          )}
        </ComboboxList>
        <ComboboxEmpty>{t('common.none')}</ComboboxEmpty>
      </ComboboxContent>
    </Combobox>
  );
}
