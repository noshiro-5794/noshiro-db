import { useState } from 'react';
import { Collapsible } from '@base-ui/react/collapsible';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ExternalLink } from 'lucide-react';
import { subjectQueries } from '@/entities/subject';
import type { SubjectDetail } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { useMediaQuery } from '@/shared/lib/use-media-query';
import { Button } from '@/shared/ui/Button';
import { ErrorState } from '@/shared/ui/FeedbackState';
import { FilterCombobox } from '@/shared/ui/FilterCombobox';
import { Pagination } from '@/shared/ui/Pagination';
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/ui/Popover';
import {
  bangumiSubjectIdOf,
  coverPlaceholder,
  getInfoboxRows,
  groupStaffByRole,
  posterOf,
  sortInfoboxRows,
  titleOf,
} from '../model/subject-detail';
import { StaffDetail, type StaffDetailLabels } from './SubjectDetailPrimitives';

const staffPageSize = 8;

export function SubjectSidebar({ subject }: { subject: SubjectDetail }) {
  const { t } = useI18n();
  const emptyText = t('common.none');
  const [staffRole, setStaffRole] = useState('');
  const [staffPage, setStaffPage] = useState(1);
  const [infoboxOpen, setInfoboxOpen] = useState(false);
  const [staffOpen, setStaffOpen] = useState(false);
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const bangumiSubjectId = bangumiSubjectIdOf(subject);
  const bangumiSnapshotQuery = useQuery({
    ...subjectQueries.bangumiSnapshot(bangumiSubjectId ?? 0),
    enabled: Boolean(bangumiSubjectId),
  });
  const staffQuery = useQuery(
    subjectQueries.staff(subject.id, {
      page: staffPage,
      page_size: staffPageSize,
      ...(staffRole ? { role: staffRole } : {}),
    }),
  );
  const staffRolesQuery = useQuery(subjectQueries.staffRoles(subject.id));
  const infoboxRows = sortInfoboxRows(getInfoboxRows(subject.infobox));
  const staffGroups = groupStaffByRole(staffQuery.data?.results ?? []);
  const staffRoleOptions = [
    { label: t('subject.allRoles'), value: '' },
    ...(staffRolesQuery.data?.roles ?? []).map((role) => ({ label: role, value: role })),
  ];
  const staffTotalPages = Math.max(1, Math.ceil((staffQuery.data?.count ?? 0) / staffPageSize));
  const bangumiSnapshot = bangumiSnapshotQuery.data;
  const bangumiRank = bangumiSnapshot?.rating?.rank ?? bangumiSnapshot?.rank;
  const bangumiUrl = bangumiSubjectId ? `https://bangumi.tv/subject/${bangumiSubjectId}` : null;
  const staffLabels: StaffDetailLabels = {
    type: t('subject.type'),
    gender: t('subject.gender'),
    birth: t('subject.birth'),
    career: t('subject.career'),
  };

  return (
    <aside className="grid content-start gap-4 self-start">
      <img
        alt={titleOf(subject, t('common.untitledSubject'))}
        className="aspect-[2/3] w-full rounded-[var(--ui-radius-surface)] bg-[var(--ui-bg-subtle)] object-cover ring-1 ring-[var(--ui-border)]"
        decoding="async"
        fetchPriority="high"
        referrerPolicy="no-referrer"
        src={posterOf(subject)}
      />

      {bangumiUrl ? (
        <section className="rounded-[var(--ui-radius-surface)] border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] p-3.5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-medium text-[var(--ui-text-muted)]">{t('subject.externalSource')}</p>
              <h2 className="mt-1 flex min-w-0 items-center gap-2 text-sm font-semibold text-[var(--ui-text)]">
                <img
                  alt=""
                  aria-hidden="true"
                  className="size-4 rounded-sm"
                  referrerPolicy="no-referrer"
                  src="https://bangumi.tv/img/favicon.ico"
                />
                <span className="truncate">Bangumi</span>
              </h2>
            </div>
            <Button asChild size="sm" type="button" variant="ghost">
              <a href={bangumiUrl} rel="noreferrer" target="_blank">
                <ExternalLink className="size-4" /> {t('common.open')}
              </a>
            </Button>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2">
            {[
              [t('subject.liveScore'), bangumiSnapshot?.rating?.score?.toFixed(1) ?? emptyText],
              [t('subject.liveRank'), bangumiRank ? `#${bangumiRank}` : emptyText],
              [t('subject.liveVotes'), bangumiSnapshot?.rating?.total ?? emptyText],
            ].map(([label, value]) => (
              <div className="rounded-[var(--ui-radius-control)] bg-[var(--ui-bg-subtle)] p-2.5" key={label}>
                <p className="text-[11px] font-medium text-[var(--ui-text-subtle)]">{label}</p>
                <p className="mt-1 text-base font-semibold text-[var(--ui-text)]">{value}</p>
              </div>
            ))}
          </div>
          {bangumiSnapshotQuery.isFetching ? (
            <p className="mt-3 text-xs text-[var(--ui-text-muted)]">{t('subject.loadingExternalSource')}</p>
          ) : null}
          {bangumiSnapshotQuery.isError ? (
            <p className="mt-3 text-xs text-[var(--ui-text-muted)]">{t('subject.externalSourceUnavailable')}</p>
          ) : null}
        </section>
      ) : null}

      <Collapsible.Root
        className="border-t border-[var(--ui-border)] pt-2 lg:pt-4"
        open={isDesktop || infoboxOpen}
        onOpenChange={setInfoboxOpen}
      >
        <div className="hidden items-center justify-between gap-3 lg:flex">
          <h2 className="text-sm font-semibold text-[var(--ui-text)]">{t('subject.infobox')}</h2>
          <span className="text-xs text-[var(--ui-text-subtle)]">
            {infoboxRows.length} {t('common.items')}
          </span>
        </div>
        <Collapsible.Trigger className="group flex h-9 w-full items-center justify-between gap-3 rounded-[var(--ui-radius-control)] px-2 text-left text-sm font-semibold text-[var(--ui-text)] outline-none transition-colors hover:bg-[var(--ui-bg-subtle)] focus-visible:ring-2 focus-visible:ring-[var(--ui-focus)] lg:hidden">
          <span>{t('subject.infobox')}</span>
          <span className="flex items-center gap-2 text-xs font-normal text-[var(--ui-text-subtle)]">
            {infoboxRows.length} {t('common.items')}
            <ChevronDown className="size-4 transition-transform group-data-[panel-open]:rotate-180" />
          </span>
        </Collapsible.Trigger>
        <Collapsible.Panel className="h-[var(--collapsible-panel-height)] overflow-hidden transition-[height] duration-150 ease-out data-[ending-style]:h-0 data-[starting-style]:h-0 [&[hidden]:not([hidden='until-found'])]:hidden">
          <dl className="mt-3 divide-y divide-[var(--ui-border)] text-sm">
            {infoboxRows.slice(0, 14).map((item) => (
              <div className="grid grid-cols-[88px_minmax(0,1fr)] gap-3 py-2.5" key={item.key}>
                <dt className="text-[var(--ui-text-muted)]">{item.key}</dt>
                <dd className="min-w-0 break-words leading-6 text-[var(--ui-text)]">{item.value}</dd>
              </div>
            ))}
            {infoboxRows.length === 0 ? (
              <div className="py-3 text-sm text-[var(--ui-text-muted)]">{emptyText}</div>
            ) : null}
          </dl>
        </Collapsible.Panel>
      </Collapsible.Root>

      <Collapsible.Root
        className="border-t border-[var(--ui-border)] pt-2 lg:pt-4"
        open={isDesktop || staffOpen}
        onOpenChange={setStaffOpen}
      >
        <div className="hidden items-center justify-between gap-3 lg:flex">
          <h2 className="text-sm font-semibold text-[var(--ui-text)]">{t('subject.staff')}</h2>
          <span className="text-xs text-[var(--ui-text-subtle)]">
            {staffQuery.data?.count ?? 0} {t('common.items')}
          </span>
        </div>
        <Collapsible.Trigger className="group flex h-9 w-full items-center justify-between gap-3 rounded-[var(--ui-radius-control)] px-2 text-left text-sm font-semibold text-[var(--ui-text)] outline-none transition-colors hover:bg-[var(--ui-bg-subtle)] focus-visible:ring-2 focus-visible:ring-[var(--ui-focus)] lg:hidden">
          <span>{t('subject.staff')}</span>
          <span className="flex items-center gap-2 text-xs font-normal text-[var(--ui-text-subtle)]">
            {staffQuery.data?.count ?? 0} {t('common.items')}
            <ChevronDown className="size-4 transition-transform group-data-[panel-open]:rotate-180" />
          </span>
        </Collapsible.Trigger>
        <Collapsible.Panel className="h-[var(--collapsible-panel-height)] overflow-hidden transition-[height] duration-150 ease-out data-[ending-style]:h-0 data-[starting-style]:h-0 [&[hidden]:not([hidden='until-found'])]:hidden">
          <div className="mt-3">
            <FilterCombobox
              label={t('subject.role')}
              options={staffRoleOptions}
              placeholder={t('subject.searchRoles')}
              value={staffRole}
              onChange={(value) => {
                setStaffRole(value);
                setStaffPage(1);
              }}
            />
          </div>
          <div className="mt-4 grid gap-3">
            {staffGroups.map(([role, members]) => (
              <div className="grid gap-2" key={role}>
                <div className="text-xs font-medium text-[var(--ui-text-subtle)]">
                  {role === 'Staff' ? t('subject.staff') : role}
                </div>
                <div className="grid gap-2">
                  {members.map((member) => (
                    <Popover key={`${role}-${member.id}`}>
                      <PopoverTrigger
                        render={
                          <Button
                            className="grid grid-cols-[36px_minmax(0,1fr)] items-center gap-2 rounded-[var(--ui-radius-control)] border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] p-2 text-left transition hover:border-[var(--ui-border-strong)] hover:bg-[var(--ui-bg-subtle)]"
                            variant="unstyled"
                          />
                        }
                      >
                        <img
                          alt=""
                          className="size-9 rounded-md bg-[var(--ui-bg-subtle)] object-cover"
                          decoding="async"
                          loading="lazy"
                          referrerPolicy="no-referrer"
                          src={member.image_thumbnail || coverPlaceholder}
                        />
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-semibold text-[var(--ui-text)]">
                            {member.name}
                          </span>
                          <span className="block truncate text-xs text-[var(--ui-text-muted)]">
                            {member.type || (role === 'Staff' ? t('subject.staff') : role)}
                          </span>
                        </span>
                      </PopoverTrigger>
                      <PopoverContent
                        align="start"
                        className="max-h-[min(640px,calc(100dvh-2rem))] w-[min(420px,calc(100vw-2rem))] overflow-y-auto p-4"
                        side="right"
                      >
                        <StaffDetail
                          emptyLabel={emptyText}
                          labels={staffLabels}
                          role={role === 'Staff' ? t('subject.staff') : role}
                          staff={member}
                        />
                      </PopoverContent>
                    </Popover>
                  ))}
                </div>
              </div>
            ))}
            {staffQuery.isFetching ? (
              <p className="text-sm text-[var(--ui-text-muted)]">{t('subject.loadingStaff')}</p>
            ) : null}
            {staffQuery.isError ? (
              <div className="grid gap-2">
                <ErrorState title={t('subject.staff')} description={t('common.requestFailed')} />
                <Button className="w-fit" size="sm" variant="secondary" onClick={() => void staffQuery.refetch()}>
                  {t('common.retry')}
                </Button>
              </div>
            ) : null}
            {!staffQuery.isFetching && !staffQuery.isError && staffGroups.length === 0 ? (
              <p className="text-sm text-[var(--ui-text-muted)]">{emptyText}</p>
            ) : null}
            <Pagination currentPage={staffPage} totalPages={staffTotalPages} onPageChange={setStaffPage} />
          </div>
        </Collapsible.Panel>
      </Collapsible.Root>
    </aside>
  );
}
