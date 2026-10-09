import { useEffect, useRef, useState } from 'react';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';

const sectionLinks = [
  ['#mark', 'subject.mark'],
  ['#reviews', 'reviews.title'],
  ['#episodes', 'subject.episodes'],
  ['#description', 'subject.description'],
  ['#characters', 'subject.characters'],
  ['#relations', 'subject.relations'],
  ['#public-reviews', 'subject.publicReviews'],
] as const;

export function SubjectSectionNav() {
  const { t } = useI18n();
  const navRef = useRef<HTMLElement>(null);
  const [activeHref, setActiveHref] = useState<(typeof sectionLinks)[number][0]>('#mark');

  useEffect(() => {
    const nav = navRef.current;
    if (!nav) return;
    const sections = sectionLinks.flatMap(([href]) => {
      const element = document.getElementById(href.slice(1));
      return element ? [{ element, href }] : [];
    });
    if (sections.length === 0) return;

    let animationFrame = 0;
    const updateActiveSection = () => {
      animationFrame = 0;
      const stickyTop = Number.parseFloat(getComputedStyle(nav).getPropertyValue('--ui-sticky-content-top')) || 0;
      const threshold = stickyTop + nav.offsetHeight + 16;
      let nextActive = sections[0]?.href ?? '#mark';

      for (const section of sections) {
        if (section.element.getBoundingClientRect().top > threshold) break;
        nextActive = section.href;
      }
      setActiveHref(nextActive);
    };
    const scheduleUpdate = () => {
      if (animationFrame) return;
      animationFrame = requestAnimationFrame(updateActiveSection);
    };

    scheduleUpdate();
    window.addEventListener('resize', scheduleUpdate);
    window.addEventListener('scroll', scheduleUpdate, { passive: true });
    return () => {
      cancelAnimationFrame(animationFrame);
      window.removeEventListener('resize', scheduleUpdate);
      window.removeEventListener('scroll', scheduleUpdate);
    };
  }, []);

  return (
    <nav
      aria-label={t('subject.title')}
      className="sticky top-[var(--ui-sticky-content-top)] z-[var(--ui-layer-sticky-content)] -mx-4 -mt-4 mb-5 border-b border-border-subtle bg-[color-mix(in_srgb,var(--ui-bg-canvas)_92%,transparent)] px-4 backdrop-blur-xl sm:-mx-5 sm:px-5 lg:-mt-5"
      data-slot="subject-section-nav"
      ref={navRef}
    >
      <div
        className="flex max-w-full gap-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        data-slot="subject-section-links"
      >
        {sectionLinks.map(([href, label]) => (
          <a
            aria-current={activeHref === href ? 'location' : undefined}
            className={cn(
              'inline-flex h-9 shrink-0 items-center border-b-2 border-transparent px-2.5 text-xs font-medium text-muted-foreground transition-[color,border-color,background-color] duration-[var(--ui-transition-fast)] hover:bg-muted hover:text-foreground',
              activeHref === href && 'border-[var(--ui-accent)] text-foreground',
            )}
            href={href}
            key={href}
            onClick={() => {
              setActiveHref(href);
            }}
          >
            {t(label)}
          </a>
        ))}
      </div>
    </nav>
  );
}
