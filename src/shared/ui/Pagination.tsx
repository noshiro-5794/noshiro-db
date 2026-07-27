import { type FormEvent, useState } from 'react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/ui/Popover';

type PaginationProps = {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
};

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  const { t } = useI18n();
  const [jumpPage, setJumpPage] = useState(String(currentPage));
  const [isJumpOpen, setIsJumpOpen] = useState(false);

  if (totalPages <= 1) return null;

  function goToPage(page: number) {
    onPageChange(Math.min(Math.max(page, 1), totalPages));
  }

  function handleJumpSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextPage = Number(jumpPage);
    if (!Number.isFinite(nextPage)) return;
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
    <div className="pagination-bar">
      <div className="pagination-bar-side">
        <Button
          className="pagination-bar-button"
          aria-label={t('common.firstPage')}
          disabled={currentPage <= 1}
          size="icon"
          type="button"
          variant="ghost"
          onClick={() => goToPage(1)}
        >
          <ChevronsLeft className="size-4" />
        </Button>
        <Button
          className="pagination-bar-button"
          aria-label={t('common.previousPage')}
          disabled={currentPage <= 1}
          size="icon"
          type="button"
          variant="ghost"
          onClick={() => goToPage(currentPage - 1)}
        >
          <ChevronLeft className="size-4" />
        </Button>
      </div>
      <Popover open={isJumpOpen} onOpenChange={handleJumpOpenChange}>
        <PopoverTrigger asChild>
          <button className="pagination-bar-status" type="button" aria-label={t('common.jumpToPage')}>
            <span>
              {t('common.page')} {currentPage}
            </span>
            <span>
              {t('common.of')} {totalPages}
            </span>
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-[min(15rem,calc(100vw-1.5rem))] p-3" side="top">
          <form className="grid gap-3" onSubmit={handleJumpSubmit}>
            <label className="grid gap-1.5">
              <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400">
                {t('common.jumpToPage')}
              </span>
              <Input
                className="h-10 rounded-lg px-3"
                inputMode="numeric"
                max={totalPages}
                min={1}
                type="number"
                value={jumpPage}
                aria-label={t('common.pageNumber')}
                onChange={(event) => setJumpPage(event.target.value)}
              />
            </label>
            <Button className="h-9" size="sm" type="submit">
              {t('common.apply')}
            </Button>
          </form>
        </PopoverContent>
      </Popover>
      <div className="pagination-bar-side justify-end">
        <Button
          className="pagination-bar-button"
          aria-label={t('common.nextPage')}
          disabled={currentPage >= totalPages}
          size="icon"
          type="button"
          variant="ghost"
          onClick={() => goToPage(currentPage + 1)}
        >
          <ChevronRight className="size-4" />
        </Button>
        <Button
          className="pagination-bar-button"
          aria-label={t('common.lastPage')}
          disabled={currentPage >= totalPages}
          size="icon"
          type="button"
          variant="ghost"
          onClick={() => goToPage(totalPages)}
        >
          <ChevronsRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}
