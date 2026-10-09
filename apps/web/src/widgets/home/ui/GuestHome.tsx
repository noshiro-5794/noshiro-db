import { LandingHero } from './LandingHero';
import { SearchShowcase } from './SearchShowcase';
import { SeasonSpotlight } from './SeasonSpotlight';

/**
 * Public landing page.
 *
 * Every band is the product rather than a picture of it: the season board, then
 * the search over real works.
 */
export function GuestHome() {
  return (
    <>
      <LandingHero />
      <SeasonSpotlight />
      <SearchShowcase />
    </>
  );
}

/** Shown while the session is being resolved, so the page does not jump. */
export function SessionCheckingHome() {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="h-44 rounded-lg border border-[var(--ui-border)] bg-[var(--ui-bg-subtle)] sm:col-span-2" />
      <div className="h-44 rounded-lg border border-[var(--ui-border)] bg-[var(--ui-bg-subtle)]" />
    </div>
  );
}
