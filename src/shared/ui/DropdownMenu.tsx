import type { ComponentProps } from 'react';
import { Menu } from '@base-ui/react/menu';
import { Check } from 'lucide-react';
import { cn } from '@/shared/lib/cn';

const DropdownMenu = Menu.Root;

function DropdownMenuGroup(props: ComponentProps<typeof Menu.Group>) {
  return <Menu.Group data-slot="dropdown-menu-group" {...props} />;
}

function DropdownMenuTrigger(props: ComponentProps<typeof Menu.Trigger>) {
  return <Menu.Trigger data-slot="dropdown-menu-trigger" {...props} />;
}

type DropdownMenuContentProps = ComponentProps<typeof Menu.Popup> &
  Pick<ComponentProps<typeof Menu.Positioner>, 'align' | 'alignOffset' | 'collisionAvoidance' | 'side' | 'sideOffset'>;

function DropdownMenuContent({
  align = 'start',
  alignOffset,
  className,
  collisionAvoidance,
  side = 'bottom',
  sideOffset = 6,
  ...props
}: DropdownMenuContentProps) {
  return (
    <Menu.Portal>
      <Menu.Positioner
        align={align}
        alignOffset={alignOffset}
        className="z-50 outline-none"
        collisionAvoidance={collisionAvoidance}
        side={side}
        sideOffset={sideOffset}
      >
        <Menu.Popup
          className={cn(
            'min-w-44 origin-[var(--transform-origin)] overflow-hidden rounded-sm border border-border bg-elevated p-1 text-foreground shadow-[var(--ui-shadow-popup)] outline-none transition-[opacity,transform] duration-[var(--ui-transition-fast)] data-[ending-style]:scale-[0.985] data-[ending-style]:opacity-0 data-[starting-style]:scale-[0.985] data-[starting-style]:opacity-0',
            className,
          )}
          data-slot="dropdown-menu-content"
          {...props}
        />
      </Menu.Positioner>
    </Menu.Portal>
  );
}

type DropdownMenuItemProps = ComponentProps<typeof Menu.Item> & {
  inset?: boolean;
};

function DropdownMenuItem({ className, inset, ...props }: DropdownMenuItemProps) {
  return (
    <Menu.Item
      className={cn(
        'relative flex min-h-8 cursor-default select-none items-center rounded-sm px-2.5 py-1.5 text-[13px] outline-none data-[disabled]:pointer-events-none data-[disabled]:opacity-45 data-[highlighted]:bg-muted data-[highlighted]:text-foreground',
        inset && 'pl-8',
        className,
      )}
      data-slot="dropdown-menu-item"
      {...props}
    />
  );
}

function DropdownMenuLabel({ className, ...props }: ComponentProps<typeof Menu.GroupLabel>) {
  return (
    <Menu.GroupLabel
      className={cn('px-2.5 py-1.5 text-[11px] font-medium text-subtle-foreground', className)}
      data-slot="dropdown-menu-label"
      {...props}
    />
  );
}

function DropdownMenuSeparator({ className, ...props }: ComponentProps<typeof Menu.Separator>) {
  return (
    <Menu.Separator
      className={cn('-mx-1 my-1 h-px bg-border-subtle', className)}
      data-slot="dropdown-menu-separator"
      {...props}
    />
  );
}

function DropdownMenuRadioGroup({ ...props }: ComponentProps<typeof Menu.RadioGroup>) {
  return <Menu.RadioGroup data-slot="dropdown-menu-radio-group" {...props} />;
}

function DropdownMenuRadioItem({ children, className, ...props }: ComponentProps<typeof Menu.RadioItem>) {
  return (
    <Menu.RadioItem
      className={cn(
        'relative flex min-h-8 cursor-default select-none items-center justify-between gap-3 rounded-sm px-2.5 py-1.5 text-[13px] outline-none data-[disabled]:pointer-events-none data-[disabled]:opacity-45 data-[highlighted]:bg-muted data-[highlighted]:text-foreground',
        className,
      )}
      data-slot="dropdown-menu-radio-item"
      {...props}
    >
      <span className="min-w-0 truncate">{children}</span>
      <span
        className="grid size-4 shrink-0 place-items-center text-[var(--ui-accent-text)]"
        data-slot="dropdown-menu-radio-item-indicator"
      >
        <Menu.RadioItemIndicator>
          <Check className="size-3.5" strokeWidth={2.25} />
        </Menu.RadioItemIndicator>
      </span>
    </Menu.RadioItem>
  );
}

export {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
};
