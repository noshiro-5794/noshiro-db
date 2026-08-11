import type { ComponentProps } from 'react';
import { Combobox as BaseCombobox } from '@base-ui/react/combobox';
import { Check, ChevronDown } from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import { InputGroupInput } from '@/shared/ui/InputGroup';

const Combobox = BaseCombobox.Root;

function ComboboxInput({ className, ...props }: ComponentProps<typeof BaseCombobox.Input>) {
  return (
    <BaseCombobox.Input className={className} data-slot="combobox-input" render={<InputGroupInput />} {...props} />
  );
}

function ComboboxTrigger({ className, ...props }: ComponentProps<typeof BaseCombobox.Trigger>) {
  return (
    <BaseCombobox.Trigger
      className={cn(
        'group/combobox-trigger grid size-7 shrink-0 place-items-center rounded-sm text-subtle-foreground outline-none transition-colors duration-[var(--ui-transition-fast)] hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring',
        className,
      )}
      data-slot="combobox-trigger"
      {...props}
    >
      <ChevronDown className="size-4 transition-transform duration-[var(--ui-transition-fast)] group-data-[popup-open]/combobox-trigger:rotate-180" />
    </BaseCombobox.Trigger>
  );
}

type ComboboxContentProps = ComponentProps<typeof BaseCombobox.Popup> &
  Pick<ComponentProps<typeof BaseCombobox.Positioner>, 'align' | 'alignOffset' | 'side' | 'sideOffset'>;

function ComboboxContent({
  align = 'start',
  alignOffset,
  className,
  side = 'bottom',
  sideOffset = 6,
  ...props
}: ComboboxContentProps) {
  return (
    <BaseCombobox.Portal>
      <BaseCombobox.Positioner
        align={align}
        alignOffset={alignOffset}
        className="isolate z-50"
        side={side}
        sideOffset={sideOffset}
      >
        <BaseCombobox.Popup
          className={cn(
            'relative max-h-[var(--available-height)] w-[var(--anchor-width)] min-w-44 origin-[var(--transform-origin)] overflow-hidden rounded-sm border border-border bg-elevated text-foreground shadow-[var(--ui-shadow-popup)] outline-none transition-[opacity,transform] duration-[var(--ui-transition-fast)] data-[ending-style]:scale-[0.985] data-[ending-style]:opacity-0 data-[starting-style]:scale-[0.985] data-[starting-style]:opacity-0',
            className,
          )}
          data-slot="combobox-content"
          {...props}
        />
      </BaseCombobox.Positioner>
    </BaseCombobox.Portal>
  );
}

function ComboboxList({ className, ...props }: ComponentProps<typeof BaseCombobox.List>) {
  return (
    <BaseCombobox.List
      className={cn('max-h-60 overflow-y-auto overscroll-contain p-1', className)}
      data-slot="combobox-list"
      {...props}
    />
  );
}

function ComboboxItem({ children, className, ...props }: ComponentProps<typeof BaseCombobox.Item>) {
  return (
    <BaseCombobox.Item
      className={cn(
        'relative flex min-h-8 w-full cursor-default select-none items-center justify-between gap-3 rounded-sm px-2.5 py-1.5 text-[13px] outline-none data-[disabled]:pointer-events-none data-[disabled]:opacity-45 data-[highlighted]:bg-muted data-[highlighted]:text-foreground',
        className,
      )}
      data-slot="combobox-item"
      {...props}
    >
      <span className="min-w-0 truncate">{children}</span>
      <span
        className="grid size-4 shrink-0 place-items-center text-[var(--ui-accent-text)]"
        data-slot="combobox-item-indicator"
      >
        <BaseCombobox.ItemIndicator>
          <Check className="size-3.5" strokeWidth={2.25} />
        </BaseCombobox.ItemIndicator>
      </span>
    </BaseCombobox.Item>
  );
}

function ComboboxEmpty({ className, ...props }: ComponentProps<typeof BaseCombobox.Empty>) {
  return (
    <BaseCombobox.Empty
      className={cn('px-3 py-6 text-center text-xs text-muted-foreground', className)}
      data-slot="combobox-empty"
      {...props}
    />
  );
}

export { Combobox, ComboboxContent, ComboboxEmpty, ComboboxInput, ComboboxItem, ComboboxList, ComboboxTrigger };
