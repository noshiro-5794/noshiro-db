import { LandingCapabilities } from './LandingCapabilities';
import { LandingClosingCta } from './LandingClosingCta';
import { LandingHero } from './LandingHero';
import { SearchShowcase } from './SearchShowcase';
import { SeasonSpotlight } from './SeasonSpotlight';

/**
 * Public landing page.
 *
 * Everything here is the product itself rather than a picture of it: the season
 * board, the search results, the works behind them. A visitor should be able to
 * tell what they get — and try it — without an account.
 */
export function GuestHome() {
  return (
    <>
      <LandingHero />
      <SeasonSpotlight />
      <SearchShowcase />
      <LandingCapabilities />
      <LandingClosingCta />
    </>
  );
}

export function SessionCheckingHome() {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="h-44 rounded-lg border border-[var(--ui-border)] bg-[var(--ui-bg-subtle)] sm:col-span-2" />
      <div className="h-44 rounded-lg border border-[var(--ui-border)] bg-[var(--ui-bg-subtle)]" />
    </div>
  );
}
