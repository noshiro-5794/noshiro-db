import type { ComponentProps } from 'react';
import { cn } from '@/shared/lib/cn';
import { Input } from '@/shared/ui/Input';

function InputGroup({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'group/input-group relative flex h-[var(--ui-control-height-lg)] w-full min-w-0 items-center rounded-sm border border-control-border bg-elevated shadow-[var(--ui-shadow-control)] outline-none transition-[border-color,box-shadow,background-color] duration-[var(--ui-transition-fast)] hover:border-[var(--ui-border-strong)] focus-within:border-ring focus-within:ring-2 focus-within:ring-[var(--ui-focus-halo)] has-[input[aria-invalid=true]]:border-destructive has-[input[aria-invalid=true]]:ring-2 has-[input[aria-invalid=true]]:ring-[var(--ui-danger-soft)]',
        className,
      )}
      data-slot="input-group"
      role="group"
      {...props}
    />
  );
}

function InputGroupAddon({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'flex h-full shrink-0 cursor-text items-center justify-center pl-3 text-subtle-foreground [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
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
