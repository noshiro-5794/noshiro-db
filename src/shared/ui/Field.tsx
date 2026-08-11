import type { ComponentProps } from 'react';
import { Field as BaseField } from '@base-ui/react/field';
import { cn } from '@/shared/lib/cn';

type FieldProps = ComponentProps<typeof BaseField.Root> & {
  orientation?: 'horizontal' | 'responsive' | 'vertical';
};

const orientationClasses: Record<NonNullable<FieldProps['orientation']>, string> = {
  vertical: 'flex-col items-stretch',
  horizontal: 'flex-row items-start gap-4',
  responsive: 'flex-col items-stretch sm:flex-row sm:items-start sm:gap-4',
};

function Field({ className, invalid = false, orientation = 'vertical', ...props }: FieldProps) {
  return (
    <BaseField.Root
      className={cn('group/field flex w-full gap-2', orientationClasses[orientation], className)}
      data-orientation={orientation}
      data-slot="field"
      invalid={invalid}
      {...props}
    />
  );
}

function FieldLabel({ className, ...props }: ComponentProps<typeof BaseField.Label>) {
  return (
    <BaseField.Label
      className={cn(
        'flex w-fit items-center gap-2 text-[13px] font-medium leading-5 text-foreground group-data-[invalid]/field:text-destructive',
        className,
      )}
      data-slot="field-label"
      {...props}
    />
  );
}

function FieldDescription({ className, ...props }: ComponentProps<typeof BaseField.Description>) {
  return (
    <BaseField.Description
      className={cn('text-xs leading-5 text-muted-foreground', className)}
      data-slot="field-description"
      {...props}
    />
  );
}

function FieldError({ className, ...props }: ComponentProps<typeof BaseField.Error>) {
  return (
    <BaseField.Error
      className={cn('text-xs font-medium leading-5 text-destructive', className)}
      data-slot="field-error"
      {...props}
    />
  );
}

export { Field, FieldDescription, FieldError, FieldLabel };
