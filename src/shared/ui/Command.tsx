import * as React from 'react';
import { Command as CommandPrimitive } from 'cmdk';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

function Command({ className, ...props }: React.ComponentProps<typeof CommandPrimitive>) {
  return <CommandPrimitive className={cn('flex h-full w-full flex-col overflow-hidden rounded-xl bg-white text-neutral-950 dark:bg-neutral-950 dark:text-white', className)} {...props} />;
}

function CommandInput({ className, ...props }: React.ComponentProps<typeof CommandPrimitive.Input>) {
  return (
    <div className="flex items-center border-b border-neutral-200 px-3 dark:border-neutral-800">
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
  return <CommandPrimitive.Empty className="py-6 text-center text-sm text-neutral-500 dark:text-neutral-400" {...props} />;
}

function CommandGroup({ className, ...props }: React.ComponentProps<typeof CommandPrimitive.Group>) {
  return <CommandPrimitive.Group className={cn('overflow-hidden p-1.5 text-neutral-950 dark:text-white', className)} {...props} />;
}

function CommandItem({ className, ...props }: React.ComponentProps<typeof CommandPrimitive.Item>) {
  return (
    <CommandPrimitive.Item
      className={cn(
        'relative flex cursor-default select-none items-center rounded-lg px-3 py-2 text-sm outline-none data-[disabled=true]:pointer-events-none data-[selected=true]:bg-neutral-100 data-[selected=true]:text-neutral-950 data-[disabled=true]:opacity-50 dark:data-[selected=true]:bg-neutral-900 dark:data-[selected=true]:text-white',
        className,
      )}
      {...props}
    />
  );
}

export { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList };
