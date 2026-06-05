import * as React from 'react';
import { Command as CommandPrimitive } from 'cmdk';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

function Command({ className, ...props }: React.ComponentProps<typeof CommandPrimitive>) {
  return <CommandPrimitive className={cn('flex h-full w-full flex-col overflow-hidden rounded-xl bg-[var(--color-surface-elevated)] text-[var(--color-text)]', className)} {...props} />;
}

function CommandInput({ className, ...props }: React.ComponentProps<typeof CommandPrimitive.Input>) {
  return (
    <div className="flex items-center border-b border-[var(--color-border)] px-3">
      <Search className="mr-2 size-4 shrink-0 text-neutral-400" />
      <CommandPrimitive.Input
        className={cn('flex h-11 w-full bg-transparent text-sm outline-none placeholder:text-neutral-400 disabled:cursor-not-allowed disabled:opacity-50', className)}
        {...props}
      />
    </div>
  );
}

function CommandList({ className, ...props }: React.ComponentProps<typeof CommandPrimitive.List>) {
  return <CommandPrimitive.List className={cn('max-h-80 overflow-y-auto overflow-x-hidden', className)} {...props} />;
}

function CommandEmpty(props: React.ComponentProps<typeof CommandPrimitive.Empty>) {
  return <CommandPrimitive.Empty className="py-6 text-center text-sm text-[var(--color-text-muted)]" {...props} />;
}

function CommandGroup({ className, ...props }: React.ComponentProps<typeof CommandPrimitive.Group>) {
  return <CommandPrimitive.Group className={cn('overflow-hidden p-1.5 text-[var(--color-text)]', className)} {...props} />;
}

function CommandItem({ className, ...props }: React.ComponentProps<typeof CommandPrimitive.Item>) {
  return (
    <CommandPrimitive.Item
      className={cn(
        'relative flex cursor-default select-none items-center rounded-lg px-3 py-2 text-sm outline-none data-[disabled=true]:pointer-events-none data-[selected=true]:bg-[var(--color-surface-muted)] data-[selected=true]:text-[var(--color-text)] data-[disabled=true]:opacity-50',
        className,
      )}
      {...props}
    />
  );
}

export { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList };
