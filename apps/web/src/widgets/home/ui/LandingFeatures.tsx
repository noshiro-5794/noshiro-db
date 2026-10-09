import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import { CollectionGraphic, ProgressGraphic, ScheduleGraphic, SearchGraphic } from './feature-graphics';
import { LandingSection } from './LandingSection';

/**
 * What a visitor can do here, in four cells.
 *
 * dub's feature band: a centred intro, then a two-column grid whose only
 * separators are hairlines — no cards, no shadows — each cell pairing one line
 * of copy with a small piece of the real interface.
 */
export function LandingFeatures() {
  const { t } = useI18n();
  const features = [
    { body: t('public.whySearchBody'), graphic: <SearchGraphic />, title: t('public.whySearchTitle') },
    { body: t('public.whyScheduleBody'), graphic: <ScheduleGraphic />, title: t('public.whyScheduleTitle') },
    { body: t('public.whyTrackBody'), graphic: <ProgressGraphic />, title: t('public.whyTrackTitle') },
    { body: t('public.whyListsBody'), graphic: <CollectionGraphic />, title: t('public.whyListsTitle') },
  ];

  return (
    <LandingSection
      className="pt-20 sm:pt-28"
      eyebrow="Noshiro DB"
      note={t('public.whyBody')}
      title={t('public.whyHeading')}
    >
      <div className="mx-auto grid max-w-[1000px] grid-cols-1 sm:grid-cols-2">
        {features.map((feature, index) => (
          <article
            className={cn(
              'grid content-start gap-5 py-8',
              index > 0 && 'border-t border-[var(--ui-border-subtle)]',
              index % 2 === 1 && 'sm:border-l sm:border-[var(--ui-border-subtle)] sm:pl-10',
              index % 2 === 0 && 'sm:pr-10',
              index > 1 && 'sm:border-t sm:pt-10',
              index < 2 && 'sm:pb-10',
            )}
            key={feature.title}
          >
            <div className="grid h-[132px] content-center rounded-[var(--ui-radius-frame)] border border-[var(--ui-border-subtle)] bg-[var(--ui-bg-surface)] px-4">
              {feature.graphic}
            </div>
            <h3 className="text-[15px] font-medium text-[var(--ui-text)]">{feature.title}</h3>
            <p className="text-[13px] leading-6 text-[var(--ui-text-muted)]">{feature.body}</p>
          </article>
        ))}
      </div>
    </LandingSection>
  );
}
