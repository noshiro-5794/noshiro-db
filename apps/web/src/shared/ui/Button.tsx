import { cloneElement, isValidElement, type ComponentProps, type MouseEvent, type ReactNode } from 'react';
import { Button as BaseButton } from '@base-ui/react/button';
import { cn } from '@/shared/lib/cn';
import { Tooltip } from '@/shared/ui/Tooltip';

type ButtonVariant = 'default' | 'secondary' | 'ghost' | 'accent' | 'destructive' | 'unstyled';
type ButtonSize = 'default' | 'xs' | 'sm' | 'lg' | 'icon' | 'icon-sm' | 'icon-lg';

const variantClasses: Record<ButtonVariant, string> = {
  default:
    'border-primary bg-primary text-primary-foreground shadow-[var(--ui-shadow-control)] hover:border-primary-hover hover:bg-primary-hover',
  secondary:
    'border-control-border bg-elevated text-foreground shadow-[var(--ui-shadow-control)] hover:border-[var(--ui-border-strong)] hover:bg-muted',
  ghost: 'border-transparent bg-transparent text-muted-foreground shadow-none hover:bg-muted hover:text-foreground',
  accent:
    'border-[var(--ui-accent-solid)] bg-[var(--ui-accent-solid)] text-[var(--ui-accent-solid-text)] shadow-[var(--ui-shadow-control)] hover:border-[var(--ui-accent-solid-hover)] hover:bg-[var(--ui-accent-solid-hover)]',
  destructive:
    'border-destructive bg-destructive text-white shadow-[var(--ui-shadow-control)] hover:border-[var(--ui-danger-hover)] hover:bg-[var(--ui-danger-hover)]',
  unstyled: '',
};

const sizeClasses: Record<ButtonSize, string> = {
  default: 'h-[var(--ui-control-height)] px-[var(--ui-control-padding-x)]',
  xs: 'h-6 gap-1 px-[var(--ui-control-padding-x-xs)] text-xs [&_svg]:size-[var(--ui-control-glyph-sm)]',
  sm: 'h-[var(--ui-control-height-xs)] px-[var(--ui-control-padding-x-xs)] text-xs [&_svg]:size-[var(--ui-control-glyph-sm)]',
  lg: 'h-[var(--ui-control-height-lg)] px-[var(--ui-control-padding-x-lg)]',
  icon: 'size-[var(--ui-control-height)] px-0',
  'icon-sm': 'size-[var(--ui-control-height-xs)] px-0 [&_svg]:size-3.5',
  'icon-lg': 'size-[var(--ui-control-height-lg)] px-0',
};

type ButtonProps = Omit<ComponentProps<typeof BaseButton>, 'render'> & {
  asChild?: boolean;
  size?: ButtonSize;
  tooltip?: ReactNode;
  variant?: ButtonVariant;
};

function Button({
  asChild = false,
  children,
  className,
  disabled = false,
  nativeButton,
  size = 'default',
  tooltip,
  type = 'button',
  variant = 'default',
  ...props
}: ButtonProps) {
  const child = asChild && isValidElement<Record<string, unknown>>(children) ? children : undefined;
  const isUnstyled = variant === 'unstyled';
  const isIconOnly = size === 'icon' || size === 'icon-sm' || size === 'icon-lg';
  const ariaLabel = props['aria-label'] ?? (isIconOnly && typeof tooltip === 'string' ? tooltip : undefined);
  const buttonClassName = cn(
    isUnstyled
      ? 'outline-none focus-visible:ring-2 focus-visible:ring-[var(--ui-focus-halo)] focus-visible:ring-offset-1 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-45 aria-disabled:pointer-events-none aria-disabled:opacity-45'
      : cn(
          'inline-flex shrink-0 select-none items-center justify-center gap-[var(--ui-control-gap)] whitespace-nowrap',
          'rounded-[var(--ui-radius-control)] border text-[13px] font-medium outline-none',
          'transition-[color,background-color,border-color,box-shadow,transform] duration-[var(--ui-transition-fast)] ease-[var(--ui-ease-gentle)]',
          // The press is a half pixel, the way a control feels rather than moves.
          'active:translate-y-[0.5px]',
          'focus-visible:ring-2 focus-visible:ring-[var(--ui-focus-halo)] focus-visible:ring-offset-1 focus-visible:ring-offset-background',
          'disabled:pointer-events-none disabled:opacity-45 aria-disabled:pointer-events-none aria-disabled:opacity-45',
          'aria-busy:pointer-events-none aria-busy:opacity-60',
          '[&_svg]:pointer-events-none [&_svg]:size-[var(--ui-control-glyph)] [&_svg]:shrink-0',
        ),
    variantClasses[variant],
    !isUnstyled && sizeClasses[size],
    className,
  );

  const button = child ? (
    cloneElement(child, {
      ...props,
      'aria-disabled': disabled || undefined,
      'aria-label': ariaLabel,
      className: cn(
        buttonClassName,
        typeof child.props['className'] === 'string' ? child.props['className'] : undefined,
      ),
      'data-slot': 'button',
      'data-size': size,
      'data-variant': variant,
      ...(disabled
        ? {
            onClick: (event: MouseEvent<HTMLElement>) => {
              event.preventDefault();
              event.stopPropagation();
            },
            tabIndex: -1,
          }
        : {}),
    })
  ) : (
    <BaseButton
      aria-label={ariaLabel}
      className={buttonClassName}
      data-size={size}
      data-slot="button"
      data-variant={variant}
      disabled={disabled}
      nativeButton={nativeButton}
      type={type}
      {...props}
    >
      {children}
    </BaseButton>
  );

  return tooltip ? <Tooltip content={tooltip}>{button}</Tooltip> : button;
}

export { Button };
