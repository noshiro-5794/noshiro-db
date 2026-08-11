import type { ReactNode } from 'react';
import type { SubjectStaff } from '@/shared/api';
import { compactText, coverPlaceholder, detailRows, getInfoboxRows } from '../model/subject-detail';

function DetailList({ rows }: { rows: Array<readonly [string, string]> }) {
  if (rows.length === 0) return null;

  return (
    <dl className="grid divide-y divide-border-subtle rounded-sm bg-muted px-3 text-sm">
      {rows.map(([label, value]) => (
        <div className="grid grid-cols-[96px_minmax(0,1fr)] gap-3 px-3 py-2.5" key={label}>
          <dt className="text-muted-foreground">{label}</dt>
          <dd className="min-w-0 break-words font-medium text-foreground">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function DetailShell({
  image,
  title,
  subtitle,
  description,
  rows,
  emptyLabel,
  children,
}: {
  image?: string | null | undefined;
  title: string;
  subtitle?: string | undefined;
  description?: string | null | undefined;
  rows?: Array<readonly [string, string]>;
  emptyLabel: string;
  children?: ReactNode;
}) {
  return (
    <div className="grid gap-5">
      <div className="grid grid-cols-[84px_minmax(0,1fr)] gap-4">
        <img
          alt=""
          className="h-28 w-[84px] rounded-sm bg-muted object-cover ring-1 ring-border-subtle"
          decoding="async"
          loading="lazy"
          referrerPolicy="no-referrer"
          src={image || coverPlaceholder}
        />
        <div className="min-w-0 self-center">
          <h3 className="line-clamp-2 text-lg font-semibold tracking-normal text-foreground">{title}</h3>
          {subtitle ? <p className="mt-2 text-sm leading-6 text-muted-foreground">{subtitle}</p> : null}
        </div>
      </div>
      {rows?.length ? <DetailList rows={rows} /> : null}
      <div className="rounded-sm bg-muted p-3 text-sm leading-6 text-muted-foreground">
        {compactText(description, emptyLabel)}
      </div>
      {children}
    </div>
  );
}

export type StaffDetailLabels = { birth: string; career: string; gender: string; type: string };

export function StaffDetail({
  emptyLabel,
  labels,
  staff,
  role,
}: {
  emptyLabel: string;
  labels: StaffDetailLabels;
  staff: SubjectStaff;
  role?: string;
}) {
  return (
    <DetailShell
      image={staff.image_original || staff.image_thumbnail}
      title={staff.name}
      subtitle={staff.role || role || staff.type || undefined}
      description={staff.description}
      emptyLabel={emptyLabel}
      rows={[
        ...detailRows([
          [labels.type, staff.type],
          [labels.gender, staff.gender],
          [labels.birth, staff.birth],
          [labels.career, staff.career],
        ]),
        ...getInfoboxRows(staff.infobox)
          .slice(0, 6)
          .map((item) => [item.key, item.value] as const),
      ]}
    />
  );
}
