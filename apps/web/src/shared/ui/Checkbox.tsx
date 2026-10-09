import { useId, type ComponentProps, type ReactNode } from 'react';
import { Checkbox as BaseCheckbox } from '@base-ui/react/checkbox';
import { Check, Minus } from 'lucide-react';
import { cn } from '@/shared/lib/cn';

function Checkbox({ className, ...props }: ComponentProps<typeof BaseCheckbox.Root>) {
  return (
    <BaseCheckbox.Root
      className={cn(
        'grid size-4 shrink-0 cursor-default place-items-center rounded-[4px] border border-control-border bg-elevated text-white outline-none transition-[background-color,border-color,box-shadow] duration-[var(--ui-transition-fast)] data-[checked]:border-brand data-[checked]:bg-brand data-[disabled]:cursor-not-allowed data-[disabled]:opacity-45 data-[indeterminate]:border-brand data-[indeterminate]:bg-brand focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
        className,
      )}
      data-slot="checkbox"
      {...props}
    >
      <BaseCheckbox.Indicator data-slot="checkbox-indicator">
        {props.indeterminate ? (
          <Minus className="size-3" strokeWidth={2.5} />
        ) : (
          <Check className="size-3" strokeWidth={2.5} />
        )}
      </BaseCheckbox.Indicator>
    </BaseCheckbox.Root>
  );
}

type CheckboxFieldProps = Omit<ComponentProps<typeof BaseCheckbox.Root>, 'children' | 'className'> & {
  children: ReactNode;
  className?: string;
  controlClassName?: string;
};

function CheckboxField({ children, className, controlClassName, ...props }: CheckboxFieldProps) {
  const labelId = useId();

  return (
    <label
      className={cn('inline-flex w-fit cursor-default items-center gap-2 text-[13px] text-muted-foreground', className)}
      data-slot="checkbox-field"
    >
      <Checkbox aria-labelledby={labelId} className={controlClassName} {...props} />
      <span id={labelId}>{children}</span>
    </label>
  );
}

export { CheckboxField };
