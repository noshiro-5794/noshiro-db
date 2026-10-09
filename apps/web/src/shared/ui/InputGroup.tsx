import type { ComponentProps } from 'react';
import { cn } from '@/shared/lib/cn';
import { Input } from '@/shared/ui/Input';

type InputGroupSize = 'default' | 'lg';

const sizeClasses: Record<InputGroupSize, string> = {
  default: 'h-[var(--ui-control-height)]',
  lg: 'h-[var(--ui-control-height-lg)]',
};

type InputGroupProps = ComponentProps<'div'> & {
  /** Control rung. `lg` is the list-toolbar and form rung. */
  size?: InputGroupSize;
};

function InputGroup({ className, size = 'default', ...props }: InputGroupProps) {
  return (
    <div
      className={cn(
        'group/input-group relative flex w-full min-w-0 items-center rounded-[var(--ui-radius-control)] border border-control-border bg-elevated',
        'shadow-[var(--ui-shadow-control)] outline-none',
        // Controls carry their own type scale so an addon cannot drift a pixel off the value beside it.
        'text-[13px]',
        'transition-[border-color,box-shadow,background-color] duration-[var(--ui-transition-fast)] ease-[var(--ui-ease-gentle)]',
        'hover:border-[var(--ui-border-strong)] focus-within:border-ring focus-within:ring-2 focus-within:ring-[var(--ui-focus-halo)]',
        'has-[input[aria-invalid=true]]:border-destructive has-[input[aria-invalid=true]]:ring-2 has-[input[aria-invalid=true]]:ring-[var(--ui-danger-soft)]',
        sizeClasses[size],
        className,
      )}
      data-slot="input-group"
      data-size={size}
      role="group"
      {...props}
    />
  );
}

function InputGroupAddon({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'flex h-full shrink-0 cursor-text items-center justify-center pl-[var(--ui-control-padding-x)] text-subtle-foreground [&_svg]:pointer-events-none [&_svg]:size-[var(--ui-control-glyph)] [&_svg]:shrink-0',
        className,
      )}
      data-slot="input-group-addon"
      onClick={(event) => {
        if ((event.target as HTMLElement).closest('button')) return;
        event.currentTarget.parentElement?.querySelector('input')?.focus();
      }}
      {...props}
    />
  );
}

function InputGroupInput({ className, ...props }: ComponentProps<typeof Input>) {
  return (
    <Input
      className={cn(
        'h-full min-w-0 flex-1 border-0 bg-transparent px-2.5 shadow-none hover:border-transparent focus:border-transparent focus:ring-0',
        className,
      )}
      data-slot="input-group-control"
      {...props}
    />
  );
}

export { InputGroup, InputGroupAddon, InputGroupInput };
