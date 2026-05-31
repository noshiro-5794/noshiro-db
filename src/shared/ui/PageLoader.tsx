export function PageLoader() {
  return (
    <div className="grid min-h-screen place-items-center bg-neutral-50 text-neutral-950 dark:bg-neutral-950 dark:text-white">
      <span
        className="size-5 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-500 dark:border-neutral-800 dark:border-t-neutral-300"
        aria-label="Loading"
        role="status"
      />
    </div>
  );
}
