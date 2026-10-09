import { Slider as BaseSlider } from '@base-ui/react/slider';
import { cn } from '@/shared/lib/cn';

type SliderProps = {
  'aria-label': string;
  className?: string;
  disabled?: boolean;
  max?: number;
  min?: number;
  step?: number;
  value: number;
  onValueChange: (value: number) => void;
};

function Slider({
  'aria-label': ariaLabel,
  className,
  disabled,
  max = 100,
  min = 0,
  step = 1,
  value,
  onValueChange,
}: SliderProps) {
  return (
    <BaseSlider.Root
      className={cn('w-full data-[disabled]:opacity-45', className)}
      data-slot="slider"
      disabled={disabled}
      max={max}
      min={min}
      step={step}
      value={value}
      onValueChange={onValueChange}
    >
      <BaseSlider.Control className="flex h-6 touch-none items-center" data-slot="slider-control">
        <BaseSlider.Track className="relative h-1.5 w-full rounded-full bg-muted" data-slot="slider-track">
          <BaseSlider.Indicator className="rounded-full bg-brand" data-slot="slider-indicator" />
          <BaseSlider.Thumb
            className="size-4 rounded-full border border-brand bg-elevated shadow-[var(--ui-shadow-control)] outline-none transition-shadow duration-[var(--ui-transition-fast)] has-[input:focus-visible]:ring-2 has-[input:focus-visible]:ring-ring has-[input:focus-visible]:ring-offset-2 has-[input:focus-visible]:ring-offset-elevated"
            data-slot="slider-thumb"
            getAriaLabel={() => ariaLabel}
          />
        </BaseSlider.Track>
      </BaseSlider.Control>
    </BaseSlider.Root>
  );
}

export { Slider };
