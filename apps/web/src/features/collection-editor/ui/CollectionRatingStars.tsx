import { Star } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import { Button } from '@/shared/ui/Button';
import { collectionRatingLabel } from '../model/presentation';

export function CollectionRatingStars({
  ariaLabel,
  value,
  label,
  interactive = false,
  onChange,
}: {
  ariaLabel?: string;
  value?: number | null;
  label: string;
  interactive?: boolean;
  onChange?: (value: number | null) => void;
}) {
  const { t } = useI18n();

  return (
    <div
      aria-label={ariaLabel ?? collectionRatingLabel(value, label)}
      className="flex items-center gap-0.5"
      role={interactive ? 'group' : 'img'}
    >
      {[1, 2, 3, 4, 5].map((rating) => {
        const star = (
          <Star
            className={cn(
              'size-4',
              value && rating <= value
                ? 'fill-[var(--ui-accent)] text-[var(--ui-accent)]'
                : 'text-[var(--ui-border-strong)]',
            )}
          />
        );
        if (!interactive || !onChange) return <span key={rating}>{star}</span>;

        return (
          <Button
            aria-label={`${t('collections.rating')} ${rating}/5`}
            aria-pressed={value === rating}
            className="rounded-sm p-0.5 transition hover:bg-muted"
            key={rating}
            type="button"
            variant="unstyled"
            onClick={() => {
              onChange(value === rating ? null : rating);
            }}
          >
            {star}
          </Button>
        );
      })}
    </div>
  );
}
