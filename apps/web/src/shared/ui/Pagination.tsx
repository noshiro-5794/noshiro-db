import { type SyntheticEvent, useId, useState } from 'react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { Field, FieldLabel } from '@/shared/ui/Field';
import { Input } from '@/shared/ui/Input';
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/ui/Popover';

type PaginationProps = {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
};

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  const { t } = useI18n();
  const jumpPageId = useId();
  const [jumpPage, setJumpPage] = useState(String(currentPage));
  const [isJumpOpen, setIsJumpOpen] = useState(false);

  if (totalPages <= 1) return null;

  function goToPage(page: number) {
    onPageChange(Math.min(Math.max(page, 1), totalPages));
  }

  function handleJumpSubmit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    const nextPage = Number(jumpPage);
    if (!Number.isInteger(nextPage)) return;
    goToPage(nextPage);
    setIsJumpOpen(false);
  }

  function handleJumpOpenChange(open: boolean) {
    setIsJumpOpen(open);
    if (open) {
      setJumpPage(String(currentPage));
    }
  }

  return (
    <nav
      aria-label={t('common.pagination')}
      className="mt-3 grid grid-cols-[auto_minmax(4rem,1fr)_auto] items-center gap-1"
      data-slot="pagination"
    >
      <div className="flex min-w-0 items-center gap-0.5">
        <Button
          className="hidden size-8 text-[var(--ui-text-muted)] sm:inline-flex"
          aria-label={t('common.firstPage')}
          disabled={currentPage <= 1}
          size="icon"
          tooltip={t('common.firstPage')}
          type="button"
          variant="ghost"
          onClick={() => {
            goToPage(1);
          }}
        >
          <ChevronsLeft className="size-4" />
        </Button>
        <Button
          className="size-8 text-[var(--ui-text-muted)]"
          aria-label={t('common.previousPage')}
          disabled={currentPage <= 1}
          size="icon"
          tooltip={t('common.previousPage')}
          type="button"
          variant="ghost"
          onClick={() => {
            goToPage(currentPage - 1);
          }}
        >
          <ChevronLeft className="size-4" />
        </Button>
      </div>
      <Popover open={isJumpOpen} onOpenChange={handleJumpOpenChange}>
        <PopoverTrigger
          render={
            <Button
              className="h-8 min-w-0 gap-1 px-2 text-xs tabular-nums"
              size="sm"
              type="button"
              variant="ghost"
              aria-label={t('common.jumpToPage')}
            />
          }
        >
          <span>
            {t('common.page')} {currentPage}
          </span>
          <span>
            {t('common.of')} {totalPages}
          </span>
        </PopoverTrigger>
        <PopoverContent className="w-[min(15rem,calc(100vw-1.5rem))] p-3" side="top">
          <form className="grid gap-3" onSubmit={handleJumpSubmit}>
            <Field>
              <FieldLabel htmlFor={jumpPageId}>{t('common.jumpToPage')}</FieldLabel>
              <Input
                className="px-3"
                id={jumpPageId}
                inputMode="numeric"
                max={totalPages}
                min={1}
                step={1}
                type="number"
                value={jumpPage}
                onChange={(event) => {
                  setJumpPage(event.target.value);
                }}
              />
            </Field>
            <Button className="h-9" size="sm" type="submit">
              {t('common.apply')}
            </Button>
          </form>
        </PopoverContent>
      </Popover>
      <div className="flex min-w-0 items-center justify-end gap-0.5">
        <Button
          className="size-8 text-[var(--ui-text-muted)]"
          aria-label={t('common.nextPage')}
          disabled={currentPage >= totalPages}
          size="icon"
          tooltip={t('common.nextPage')}
          type="button"
          variant="ghost"
          onClick={() => {
            goToPage(currentPage + 1);
          }}
        >
          <ChevronRight className="size-4" />
        </Button>
        <Button
          className="hidden size-8 text-[var(--ui-text-muted)] sm:inline-flex"
          aria-label={t('common.lastPage')}
          disabled={currentPage >= totalPages}
          size="icon"
          tooltip={t('common.lastPage')}
          type="button"
          variant="ghost"
          onClick={() => {
            goToPage(totalPages);
          }}
        >
          <ChevronsRight className="size-4" />
        </Button>
      </div>
    </nav>
  );
}
