import { CalendarDays, Layers, ListChecks, Search } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { LandingSection } from './LandingSection';

/**
 * What a visitor actually gets, in their own words. Four short lines instead of
 * diagrams: each one names something the app can do for them.
 */
export function LandingCapabilities() {
  const { t } = useI18n();
  const capabilities = [
    { body: t('public.whySearchBody'), icon: Search, title: t('public.whySearchTitle') },
    { body: t('public.whyScheduleBody'), icon: CalendarDays, title: t('public.whyScheduleTitle') },
    { body: t('public.whyTrackBody'), icon: ListChecks, title: t('public.whyTrackTitle') },
    { body: t('public.whyListsBody'), icon: Layers, title: t('public.whyListsTitle') },
  ];

  return (
    <LandingSection className="pt-16 sm:pt-20" title={t('public.whyHeading')}>
      <div className="grid gap-x-10 gap-y-8 border-t border-[var(--ui-border-subtle)] pt-8 sm:grid-cols-2 lg:grid-cols-4">
        {capabilities.map((capability) => (
          <article className="grid content-start gap-3" key={capability.title}>
            <span className="grid size-8 place-items-center rounded-[var(--ui-radius-control)] border border-[var(--ui-border)] bg-[var(--ui-bg-subtle)] text-[var(--ui-text-muted)]">
              <capability.icon className="size-4" />
            </span>
            <h3 className="text-[15px] font-medium text-[var(--ui-text)]">{capability.title}</h3>
            <p className="text-[13px] leading-6 text-[var(--ui-text-muted)]">{capability.body}</p>
          </article>
        ))}
      </div>
    </LandingSection>
  );
}
