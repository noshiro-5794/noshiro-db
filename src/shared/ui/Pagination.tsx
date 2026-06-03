import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';

type PaginationItem = number | 'ellipsis';

type PaginationProps = {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
};

function buildPaginationItems(currentPage: number, totalPages: number): PaginationItem[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const pages = new Set([1, totalPages, currentPage, currentPage - 1, currentPage + 1]);
  if (currentPage <= 4) [2, 3, 4, 5].forEach((page) => pages.add(page));
  if (currentPage >= totalPages - 3) {
    [totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1].forEach((page) => pages.add(page));
  }

  const sortedPages = [...pages].filter((page) => page >= 1 && page <= totalPages).sort((a, b) => a - b);

  return sortedPages.flatMap((page, index) => {
    const previousPage = sortedPages[index - 1];
    if (!previousPage) return [page];
    if (page - previousPage === 2) return [previousPage + 1, page];
    if (page - previousPage > 2) return ['ellipsis' as const, page];
    return [page];
  });
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  const [draftPage, setDraftPage] = useState(String(currentPage));
  const paginationItems = useMemo(() => buildPaginationItems(currentPage, totalPages), [currentPage, totalPages]);

  useEffect(() => {
    setDraftPage(String(currentPage));
  }, [currentPage]);

  function goToPage(page: number) {
    onPageChange(Math.min(Math.max(page, 1), totalPages));
  }

  function handleJump(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const page = Number(draftPage);
    if (Number.isFinite(page)) {
      goToPage(page);
    }
  }

  if (totalPages <= 1) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-neutral-200 pt-5 dark:border-neutral-800">
      <Button disabled={currentPage <= 1} type="button" variant="secondary" onClick={() => goToPage(currentPage - 1)}>
        Previous
      </Button>
      {paginationItems.map((item, index) =>
        item === 'ellipsis' ? (
          <span className="px-2 text-sm text-neutral-400" key={`ellipsis-${index}`}>
            ...
          </span>
        ) : (
          <Button
            className="min-w-10 px-3"
            key={item}
            size="sm"
            type="button"
            variant={item === currentPage ? 'default' : 'secondary'}
            onClick={() => goToPage(item)}
          >
            {item}
          </Button>
        ),
      )}
      <Button disabled={currentPage >= totalPages} type="button" variant="secondary" onClick={() => goToPage(currentPage + 1)}>
        Next
      </Button>
      <form className="ml-auto flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400" onSubmit={handleJump}>
        <span>
          Page {currentPage} of {totalPages}
        </span>
        <Input
          aria-label="Jump to page"
          className="h-9 w-20 px-3"
          inputMode="numeric"
          value={draftPage}
          onChange={(event) => setDraftPage(event.target.value)}
        />
      </form>
    </div>
  );
}
