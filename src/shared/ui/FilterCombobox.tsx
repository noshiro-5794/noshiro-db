import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '@/shared/i18n';
import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
  ComboboxTrigger,
} from '@/shared/ui/Combobox';
import { InputGroup, InputGroupAddon } from '@/shared/ui/InputGroup';

type FilterComboboxOption<TValue extends string> = {
  label: string;
  value: TValue;
};

type FilterComboboxProps<TValue extends string> = {
  createValue?: (query: string) => TValue | null;
  label: string;
  options: Array<FilterComboboxOption<TValue>>;
  placeholder?: string;
  value: TValue;
  onChange: (value: TValue) => void;
};

export function FilterCombobox<TValue extends string>({
  createValue,
  label,
  options,
  placeholder,
  value,
  onChange,
}: FilterComboboxProps<TValue>) {
  const { t } = useI18n();
  const selectedOption = useMemo(
    () => options.find((option) => option.value === value) ?? (value ? { label: value, value } : null),
    [options, value],
  );
  const selectedLabel = selectedOption?.label ?? value;
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
      <InputGroup className="h-[var(--ui-control-height)]">
        <InputGroupAddon className="shrink-0 pr-0 text-xs">{label}</InputGroupAddon>
        <ComboboxInput
          aria-label={label}
          className="font-medium"
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
