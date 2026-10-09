import { LandingClosingCta } from './LandingClosingCta';
import { LandingFeatures } from './LandingFeatures';
import { LandingHero } from './LandingHero';
import { SearchShowcase } from './SearchShowcase';
import { SeasonSpotlight } from './SeasonSpotlight';

/**
 * Public landing page.
 *
 * Every band is the product rather than a picture of it: the season board, the
 * search over real works, and the four things a visitor can do with them. The
 * composition — panel hero, product bands, hairline feature grid, closing panel
 * — follows dub's site; the motion follows twenty's.
 */
export function GuestHome() {
  return (
    <>
      <LandingHero />
      <SeasonSpotlight />
      <SearchShowcase />
      <LandingFeatures />
      <LandingClosingCta />
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
