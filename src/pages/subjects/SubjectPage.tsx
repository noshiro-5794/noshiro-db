import { type FormEvent, type ReactNode, useEffect, useState } from 'react';
import { Link, useLocation, useParams } from '@/shared/routing/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  Check,
  ExternalLink,
  Eye,
  Heart,
  Network,
  Pause,
  PencilLine,
  Plus,
  ShieldAlert,
  Sparkles,
  Star,
  Trash2,
  XCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/entities/session';
import { useI18n } from '@/shared/i18n';
import { libraryMutations, libraryQueries, libraryQueryKeys } from '@/entities/library';
import { subjectQueries } from '@/entities/subject';
import type {
  ProgressSummary,
  RatingDetail,
  SubjectCharacter,
  SubjectDetail,
  SubjectEpisode,
  SubjectRelation,
  SubjectStaff,
  UserSubjectStatus,
} from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { currentRoutePath, routeBackState } from '@/shared/routing/route-state';
import { Seo } from '@/shared/seo/Seo';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/Card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterCombobox } from '@/shared/ui/FilterCombobox';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/ui/Popover';

const coverPlaceholder = '/assets/placeholders/subject-cover.png';
const staffPageSize = 8;
const episodePageSize = 12;
const otherEpisodeFetchSize = 120;
const otherEpisodePageSize = 8;
const characterPageSize = 8;
const relationFetchSize = 160;
const relationVisualPageBudget = 6.4;
const relationChunkSize = 9;
const publicReviewPageSize = 8;

type InfoboxRow = {
  key: string;
  value: string;
};

type MarkFormBody = {
  status: UserSubjectStatus;
  simple_rating?: number;
  rating?: string;
  comment: string;
  is_public: boolean;
};

const statusStyles: Record<string, { icon: typeof Heart; tone: string }> = {
  wish: { icon: Heart, tone: 'status-wish' },
  doing: { icon: Eye, tone: 'status-doing' },
  done: { icon: Check, tone: 'status-done' },
  on_hold: { icon: Pause, tone: 'status-hold' },
  drop: { icon: XCircle, tone: 'status-drop' },
};

const importantInfoboxKeys = [
  '话数',
  '放送开始',
  '放送星期',
  '上映年度',
  '发售日',
  '开发',
  '发行',
  '平台',
  '游戏类型',
  '原作',
  '导演',
  '監督',
  '脚本',
  '音乐',
  '音楽',
  '动画制作',
  '製作',
];

const importantStaffRoles = [
  '監督',
  '导演',
  'director',
  '原作',
  '脚本',
  '系列构成',
  'シリーズ構成',
  'キャラクターデザイン',
  '角色设计',
  '音楽',
  '音乐',
  '动画制作',
];

function titleOf(subject: SubjectDetail, fallback = 'Untitled') {
  return subject.display_title || subject.title || subject.title_cn || fallback;
}

function metaOf(subject: SubjectDetail) {
  return [subject.subject_type, subject.platform, subject.date].filter(Boolean).join(' · ');
}

function seoDescriptionOf(subject: SubjectDetail) {
  return (
    subject.description_excerpt ||
    subject.summary ||
    subject.description ||
    metaOf(subject) ||
    'Open anime and galgame details on Noshiro DB.'
  );
}

function seoImageOf(subject: SubjectDetail) {
  return (
    subject.images?.original ||
    subject.images?.poster ||
    subject.image_original ||
    subject.images?.thumbnail ||
    subject.image_thumbnail ||
    null
  );
}

function bangumiSubjectIdOf(subject?: SubjectDetail | null) {
  const sourceId = subject?.source?.id ?? subject?.source_id;
  if (typeof sourceId === 'number' && Number.isFinite(sourceId)) return sourceId;
  if (typeof sourceId === 'string' && /^\d+$/u.test(sourceId)) return Number(sourceId);
  return null;
}

function episodeTitle(episode: SubjectEpisode) {
  return episode.title || (episode.ep_num ? `Episode ${episode.ep_num}` : `Episode ${episode.id}`);
}

function episodeLabel(episode: SubjectEpisode) {
  if (episode.type === 'EP') {
    return `EP ${episode.ep_num ?? episode.sort ?? episode.id}`;
  }

  return [episode.type, episode.sort ?? episode.ep_num]
    .filter((item) => item !== null && item !== undefined && item !== '')
    .join(' ');
}

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function formatInfoboxValue(value: unknown): string {
  if (typeof value === 'string') {
    return value;
  }

  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item && typeof item === 'object') {
          const record = item as Record<string, unknown>;
          return [record.v, record.name, record.title].find((entry) => typeof entry === 'string');
        }
        return '';
      })
      .filter(Boolean)
      .join(' / ');
  }

  if (value && typeof value === 'object') {
    return Object.values(value as Record<string, unknown>)
      .filter((entry): entry is string => typeof entry === 'string' && Boolean(entry))
      .join(' / ');
  }

  return '';
}

function formatUnknownValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    return value.map(formatUnknownValue).filter(Boolean).join(' / ');
  }
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => {
        const formatted = formatUnknownValue(item);
        return formatted ? `${key}: ${formatted}` : '';
      })
      .filter(Boolean)
      .join(' / ');
  }
  return '';
}

function compactText(value: string | null | undefined, fallback: string) {
  const normalized = value?.trim();
  return normalized || fallback;
}

function detailRows(rows: Array<[string, unknown]>) {
  return rows
    .map(([label, value]) => [label, formatUnknownValue(value)] as const)
    .filter(([, value]) => Boolean(value));
}

function getInfoboxRows(infobox: unknown): InfoboxRow[] {
  if (!Array.isArray(infobox)) {
    return [];
  }

  return infobox
    .map((item) => {
      if (!item || typeof item !== 'object') return null;
      const record = item as Record<string, unknown>;
      const key = typeof record.key === 'string' ? record.key : '';
      const value = formatInfoboxValue(record.value);
      return key && value ? { key, value } : null;
    })
    .filter((row): row is InfoboxRow => Boolean(row));
}

function sortInfoboxRows(rows: InfoboxRow[]) {
  return [...rows].sort((a, b) => {
    const aIndex = importantInfoboxKeys.findIndex((key) => a.key.includes(key));
    const bIndex = importantInfoboxKeys.findIndex((key) => b.key.includes(key));
    const normalizedA = aIndex === -1 ? 999 : aIndex;
    const normalizedB = bIndex === -1 ? 999 : bIndex;
    return normalizedA - normalizedB;
  });
}

function groupStaffByRole(staff: SubjectStaff[]) {
  const groups = new Map<string, SubjectStaff[]>();

  for (const item of staff) {
    const role = item.role?.trim() || 'Staff';
    const current = groups.get(role) ?? [];
    current.push(item);
    groups.set(role, current);
  }

  return [...groups.entries()].sort(([roleA], [roleB]) => {
    const aIndex = importantStaffRoles.findIndex((role) => roleA.toLowerCase().includes(role.toLowerCase()));
    const bIndex = importantStaffRoles.findIndex((role) => roleB.toLowerCase().includes(role.toLowerCase()));
    const normalizedA = aIndex === -1 ? 999 : aIndex;
    const normalizedB = bIndex === -1 ? 999 : bIndex;
    return normalizedA - normalizedB || roleA.localeCompare(roleB);
  });
}

function relationSortWeight(relation: SubjectRelation) {
  const label = relation.relation?.toLowerCase() ?? '';
  if (label.includes('前') || label.includes('prequel')) return 0;
  if (label.includes('续') || label.includes('続') || label.includes('sequel')) return 1;
  if (label.includes('主') || label.includes('main')) return 2;
  if (label.includes('改编') || label.includes('adapt')) return 3;
  if (label.includes('外传') || label.includes('番外') || label.includes('side') || label.includes('spin')) return 4;
  return 20;
}

function relationSubjectTypeWeight(relation: SubjectRelation) {
  if (relation.subject.subject_type === 'anime') return 0;
  if (relation.subject.subject_type === 'galgame') return 1;
  return 2;
}

type RelationDisplayGroup = {
  key: string;
  label: string;
  tier: 'primary' | 'other';
  items: SubjectRelation[];
  totalCount: number;
};

function relationTierOf(relation: SubjectRelation): RelationDisplayGroup['tier'] {
  return isPrimaryRelation(relation) ? 'primary' : 'other';
}

function groupRelationsForDisplay(relations: SubjectRelation[], fallback: string): RelationDisplayGroup[] {
  const groups = new Map<string, RelationDisplayGroup>();

  for (const relation of relations) {
    const label = relation.relation?.trim() || fallback;
    const tier = relationTierOf(relation);
    const key = `${tier}:${label}`;
    const current = groups.get(key);
    groups.set(key, {
      key,
      label,
      tier,
      items: [...(current?.items ?? []), relation],
      totalCount: (current?.totalCount ?? 0) + 1,
    });
  }

  return [...groups.entries()]
    .map(([, group]) => ({
      ...group,
      items: [...group.items].sort(
        (a, b) =>
          relationSubjectTypeWeight(a) - relationSubjectTypeWeight(b) ||
          relationTitle(a).localeCompare(relationTitle(b)),
      ),
    }))
    .sort((a, b) => {
      const tierWeight = (group: RelationDisplayGroup) => (group.tier === 'primary' ? 0 : 1);
      return (
        tierWeight(a) - tierWeight(b) ||
        relationSortWeight(a.items[0]) - relationSortWeight(b.items[0]) ||
        a.label.localeCompare(b.label)
      );
    });
}

function relationGroupVisualCost(itemCount: number) {
  return 1 + Math.ceil(itemCount / 3);
}

function paginateRelationGroups(groups: RelationDisplayGroup[]) {
  const pages: RelationDisplayGroup[][] = [];
  let currentPage: RelationDisplayGroup[] = [];
  let currentCost = 0;

  for (const group of groups) {
    for (let index = 0; index < group.items.length; index += relationChunkSize) {
      const items = group.items.slice(index, index + relationChunkSize);
      const chunk: RelationDisplayGroup = {
        ...group,
        key: `${group.key}:${index}`,
        items,
      };
      const cost = relationGroupVisualCost(items.length);

      if (currentPage.length > 0 && currentCost + cost > relationVisualPageBudget) {
        pages.push(currentPage);
        currentPage = [];
        currentCost = 0;
      }

      currentPage.push(chunk);
      currentCost += cost;
    }
  }

  if (currentPage.length > 0) {
    pages.push(currentPage);
  }

  return pages.length ? pages : [[]];
}

function posterOf(subject: SubjectDetail) {
  return (
    subject.images?.original ||
    subject.image_original ||
    subject.images?.poster ||
    subject.image_thumbnail ||
    subject.image ||
    coverPlaceholder
  );
}

function isPrimaryRelation(relation: SubjectRelation) {
  return relation.subject.subject_type === 'anime' || relation.subject.subject_type === 'galgame';
}

function relationTitle(relation: SubjectRelation, fallback = 'Untitled') {
  return relation.subject.display_title || relation.subject.title || relation.subject.title_cn || fallback;
}

function relationMeta(relation: SubjectRelation, fallback: string) {
  const subject = relation.subject;
  const displayMeta = Array.isArray(subject.display_meta) ? subject.display_meta.filter(Boolean) : [];
  const contentMeta = [
    subject.content?.episodes ? `${subject.content.episodes} EP` : '',
    subject.content?.volumes ? `${subject.content.volumes} Vol` : '',
  ].filter(Boolean);
  return (
    [...displayMeta, subject.display_subtitle, subject.date, subject.platform, ...contentMeta]
      .filter(Boolean)
      .join(' · ') || fallback
  );
}

function subjectImage(subject: SubjectRelation['subject']) {
  return subject.images?.poster || subject.image_thumbnail || subject.image || coverPlaceholder;
}

function episodeMeta(episode: SubjectEpisode, fallback: string) {
  return (
    [episode.date, episode.duration, episode.sort !== null && episode.sort !== undefined ? `sort ${episode.sort}` : '']
      .filter(Boolean)
      .join(' · ') || fallback
  );
}

function StarRatingControl({
  clearLabel,
  disabled,
  value,
  onChange,
}: {
  clearLabel: string;
  disabled?: boolean;
  value: string;
  onChange: (value: string) => void;
}) {
  const numericValue = Number(value || 0);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="inline-flex rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] p-1">
        {[1, 2, 3, 4, 5].map((ratingValue) => {
          const active = numericValue >= ratingValue;
          return (
            <button
              aria-label={`${ratingValue} / 5`}
              className={`grid size-9 place-items-center rounded-full transition ${
                active
                  ? 'text-[var(--color-accent-strong)]'
                  : 'text-[color-mix(in_srgb,var(--color-text-muted)_45%,transparent)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-text-muted)]'
              }`}
              disabled={disabled}
              key={ratingValue}
              type="button"
              onClick={() => onChange(String(ratingValue))}
            >
              <Star className="size-4" fill={active ? 'currentColor' : 'none'} />
            </button>
          );
        })}
      </div>
      <Button disabled={disabled || !value} size="sm" type="button" variant="ghost" onClick={() => onChange('')}>
        {clearLabel}
      </Button>
    </div>
  );
}

function StarRatingDisplay({ value, emptyLabel }: { value?: number | null; emptyLabel: string }) {
  if (!value) {
    return <span className="text-sm font-semibold text-[var(--color-text)]">{emptyLabel}</span>;
  }

  return (
    <span className="inline-flex items-center gap-0.5 text-[var(--color-accent-strong)]">
      {[1, 2, 3, 4, 5].map((ratingValue) => (
        <Star className="size-3.5" fill={value >= ratingValue ? 'currentColor' : 'none'} key={ratingValue} />
      ))}
    </span>
  );
}

function DetailList({ rows }: { rows: Array<readonly [string, string]> }) {
  if (rows.length === 0) return null;

  return (
    <dl className="grid divide-y divide-[var(--color-border)] rounded-xl border border-[var(--color-border)] text-sm">
      {rows.map(([label, value]) => (
        <div className="grid grid-cols-[96px_minmax(0,1fr)] gap-3 px-3 py-2.5" key={label}>
          <dt className="text-[var(--color-text-muted)]">{label}</dt>
          <dd className="min-w-0 break-words font-medium text-[var(--color-text)]">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function DetailShell({
  image,
  title,
  subtitle,
  description,
  rows,
  emptyLabel,
  children,
}: {
  image?: string | null;
  title: string;
  subtitle?: string;
  description?: string | null;
  rows?: Array<readonly [string, string]>;
  emptyLabel: string;
  children?: ReactNode;
}) {
  return (
    <div className="grid gap-5">
      <div className="grid grid-cols-[84px_minmax(0,1fr)] gap-4">
        <img
          alt=""
          className="h-28 w-[84px] rounded-xl bg-[var(--color-surface-muted)] object-cover ring-1 ring-[var(--color-border)]"
          src={image || coverPlaceholder}
        />
        <div className="min-w-0 self-center">
          <h3 className="line-clamp-2 text-lg font-semibold tracking-tight text-[var(--color-text)]">{title}</h3>
          {subtitle ? <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{subtitle}</p> : null}
        </div>
      </div>
      {rows?.length ? <DetailList rows={rows} /> : null}
      <div className="rounded-xl bg-[var(--color-surface-muted)] p-4 text-sm leading-7 text-[var(--color-text-muted)]">
        {compactText(description, emptyLabel)}
      </div>
      {children}
    </div>
  );
}

function StaffDetail({
  emptyLabel,
  labels,
  staff,
  role,
}: {
  emptyLabel: string;
  labels: { birth: string; career: string; gender: string; type: string };
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

function RelationItemContent({
  emptyText,
  relation,
  titleFallback,
}: {
  emptyText: string;
  relation: SubjectRelation;
  titleFallback: string;
}) {
  const primary = isPrimaryRelation(relation);

  return (
    <>
      <img alt="" className="relation-item-cover" src={subjectImage(relation.subject)} />
      <div className="relation-item-body">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Badge variant={primary ? 'accent' : 'secondary'}>{relation.subject.subject_type}</Badge>
        </div>
        <h3 className="relation-item-title">{relationTitle(relation, titleFallback)}</h3>
        <p className="relation-item-meta">{relationMeta(relation, emptyText)}</p>
      </div>
    </>
  );
}

export function SubjectPage() {
  const { t } = useI18n();
  const { subjectId } = useParams();
  const location = useLocation();
  const auth = useAuth();
  const isAuthenticated = auth.isAuthenticated;
  const queryClient = useQueryClient();
  const emptyText = t('common.none');
  const statusOptions = [
    { label: t('status.wish'), value: 'wish' },
    { label: t('status.doing'), value: 'doing' },
    { label: t('status.done'), value: 'done' },
    { label: t('status.onHold'), value: 'on_hold' },
    { label: t('status.drop'), value: 'drop' },
  ] satisfies Array<{ label: string; value: UserSubjectStatus }>;
  const subjectDetailLabels = {
    type: t('subject.type'),
    gender: t('subject.gender'),
    birth: t('subject.birth'),
    career: t('subject.career'),
  };
  const [status, setStatus] = useState<UserSubjectStatus>('wish');
  const [simpleRating, setSimpleRating] = useState('');
  const [rating, setRating] = useState('');
  const [comment, setComment] = useState('');
  const [isPublic, setIsPublic] = useState(true);
  const [tagText, setTagText] = useState('');
  const [ratingDetailRows, setRatingDetailRows] = useState<RatingDetail[]>([{ key: '', value: '' }]);
  const [noticeMessage, setNoticeMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [staffRole, setStaffRole] = useState('');
  const [staffPage, setStaffPage] = useState(1);
  const [episodePage, setEpisodePage] = useState(1);
  const [otherEpisodePage, setOtherEpisodePage] = useState(1);
  const [characterPage, setCharacterPage] = useState(1);
  const [publicReviewPage, setPublicReviewPage] = useState(1);
  const [relationPage, setRelationPage] = useState(1);
  const [selectedEpisodeId, setSelectedEpisodeId] = useState<number | null>(null);
  const [selectedStaff, setSelectedStaff] = useState<SubjectStaff | null>(null);
  const [selectedCharacter, setSelectedCharacter] = useState<SubjectCharacter | null>(null);
  const [selectedRelation, setSelectedRelation] = useState<SubjectRelation | null>(null);
  const [isMarkDialogOpen, setIsMarkDialogOpen] = useState(false);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
  const [pendingEpisodeId, setPendingEpisodeId] = useState<number | null>(null);
  const selectedStatusLabel = statusOptions.find((option) => option.value === status)?.label ?? status;

  const detailQuery = useQuery({
    ...subjectQueries.detail(subjectId ?? ''),
    enabled: Boolean(subjectId),
  });
  const bangumiSubjectId = bangumiSubjectIdOf(detailQuery.data);
  const bangumiSnapshotQuery = useQuery({
    ...subjectQueries.bangumiSnapshot(bangumiSubjectId ?? 0),
    enabled: Boolean(bangumiSubjectId),
  });
  const episodesQuery = useQuery({
    ...subjectQueries.episodes(subjectId ?? '', { page: episodePage, page_size: episodePageSize, type: 'EP' }),
    enabled: Boolean(subjectId),
  });
  const otherEpisodesQuery = useQuery({
    ...subjectQueries.episodes(subjectId ?? '', { page: 1, page_size: otherEpisodeFetchSize }),
    enabled: Boolean(subjectId),
  });
  const staffQuery = useQuery({
    ...subjectQueries.staff(subjectId ?? '', {
      page: staffPage,
      page_size: staffPageSize,
      role: staffRole || undefined,
    }),
    enabled: Boolean(subjectId),
  });
  const staffRolesQuery = useQuery({
    ...subjectQueries.staffRoles(subjectId ?? ''),
    enabled: Boolean(subjectId),
  });
  const charactersQuery = useQuery({
    ...subjectQueries.characters(subjectId ?? '', { page: characterPage, page_size: characterPageSize }),
    enabled: Boolean(subjectId),
  });
  const selectedEpisodeQuery = useQuery({
    ...subjectQueries.episode(subjectId ?? '', selectedEpisodeId ?? 0),
    enabled: Boolean(subjectId) && selectedEpisodeId !== null,
  });
  const relationsQuery = useQuery({
    ...subjectQueries.relations(subjectId ?? '', { page: 1, page_size: relationFetchSize }),
    enabled: Boolean(subjectId),
  });
  const contextQuery = useQuery({
    ...libraryQueries.subjectContext(subjectId ?? ''),
    enabled: Boolean(subjectId) && isAuthenticated,
  });
  const publicReviewsQuery = useQuery({
    ...libraryQueries.publicSubjectReviews(subjectId ?? '', {
      page: publicReviewPage,
      page_size: publicReviewPageSize,
      ordering: '-created_at',
    }),
    enabled: Boolean(subjectId),
  });
  const progressQuery = useQuery({
    ...libraryQueries.progress(subjectId ?? ''),
    enabled: Boolean(subjectId) && isAuthenticated,
  });
  const tagsQuery = useQuery({
    ...libraryQueries.tags(),
    enabled: isAuthenticated,
  });

  const createSubjectMutation = useMutation(libraryMutations.createUserSubject());
  const updateSubjectMutation = useMutation(libraryMutations.updateUserSubject());
  const deleteSubjectMutation = useMutation(libraryMutations.deleteUserSubject());
  const setEpisodeFinishedMutation = useMutation(libraryMutations.setEpisodeFinished());
  const replaceTagsMutation = useMutation(libraryMutations.replaceTags());
  const replaceRatingDetailsMutation = useMutation(libraryMutations.replaceRatingDetails());

  const userSubject = contextQuery.data?.user_subject ?? null;
  const progress = progressQuery.data ?? contextQuery.data?.progress;

  useEffect(() => {
    if (!userSubject) {
      setStatus('wish');
      setSimpleRating('');
      setRating('');
      setComment('');
      setIsPublic(true);
      return;
    }

    setStatus(userSubject.status);
    setSimpleRating(userSubject.simple_rating ? String(userSubject.simple_rating) : '');
    setRating(userSubject.rating ? String(userSubject.rating) : '');
    setComment(userSubject.comment ?? '');
    setIsPublic(userSubject.is_public);
  }, [userSubject]);

  useEffect(() => {
    setTagText((contextQuery.data?.tags ?? []).map((tag) => tag.name).join(', '));
    const details = contextQuery.data?.rating_details ?? [];
    setRatingDetailRows(details.length ? details : [{ key: '', value: '' }]);
  }, [contextQuery.data?.rating_details, contextQuery.data?.tags]);

  useEffect(() => {
    setStaffPage(1);
    setEpisodePage(1);
    setOtherEpisodePage(1);
    setCharacterPage(1);
    setPublicReviewPage(1);
    setRelationPage(1);
    setSelectedEpisodeId(null);
    setSelectedStaff(null);
    setSelectedCharacter(null);
    setSelectedRelation(null);
  }, [subjectId]);

  async function refreshUserSubjectData() {
    if (!subjectId) return;
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: libraryQueryKeys.subjectContext(subjectId) }),
      queryClient.invalidateQueries({ queryKey: libraryQueryKeys.progress(subjectId) }),
      queryClient.invalidateQueries({ queryKey: libraryQueryKeys.userSubjects() }),
    ]);
  }

  async function handleMarkSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!subjectId) return;

    setNoticeMessage('');
    setErrorMessage('');
    const body = {
      status,
      simple_rating: simpleRating ? Number(simpleRating) : undefined,
      rating: rating.trim() || undefined,
      comment,
      is_public: isPublic,
    };

    await executeMarkSubmit(body);
  }

  async function executeMarkSubmit(markBody: MarkFormBody) {
    if (!subjectId) return;
    setNoticeMessage('');
    setErrorMessage('');
    try {
      if (userSubject) {
        await updateSubjectMutation.mutateAsync({
          userSubjectId: userSubject.id,
          body: markBody,
        });
        setNoticeMessage(t('subject.markUpdated'));
      } else {
        await createSubjectMutation.mutateAsync({
          subject_id: subjectId,
          ...markBody,
        });
        setNoticeMessage(t('subject.markCreated'));
      }
      const tagNames = tagText
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean);
      const details = ratingDetailRows
        .map((detail) => ({ key: detail.key.trim(), value: detail.value.trim() }))
        .filter((detail) => detail.key && detail.value);
      await replaceTagsMutation.mutateAsync({ subjectId, tagNames });
      await replaceRatingDetailsMutation.mutateAsync({ subjectId, details });
      await refreshUserSubjectData();
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.tags() });
      setIsMarkDialogOpen(false);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t('common.requestFailed'));
    }
  }

  async function handleDeleteMark() {
    if (!userSubject) return;
    setNoticeMessage('');
    setErrorMessage('');
    try {
      await deleteSubjectMutation.mutateAsync(userSubject.id);
      setNoticeMessage(t('subject.markDeleted'));
      if (subjectId) {
        queryClient.setQueryData<ProgressSummary>(libraryQueryKeys.progress(subjectId), {
          subject_id: subjectId,
          user_subject_id: null,
          total_episodes: totalPrimaryCount,
          finished_count: 0,
          finished_episode_ids: [],
          episodes: [],
        });
      }
      await refreshUserSubjectData();
      setIsDeleteConfirmOpen(false);
      setIsMarkDialogOpen(false);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t('common.requestFailed'));
      setIsDeleteConfirmOpen(false);
    }
  }

  async function handleEpisodeToggle(episodeId: number, isFinished: boolean) {
    if (!subjectId) return;
    setPendingEpisodeId(episodeId);
    try {
      const nextProgress = await setEpisodeFinishedMutation.mutateAsync({ subjectId, episodeId, isFinished });
      queryClient.setQueryData<ProgressSummary>(libraryQueryKeys.progress(subjectId), nextProgress);
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.subjectContext(subjectId) });
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.progress(subjectId) });
    } finally {
      setPendingEpisodeId(null);
    }
  }

  function handleEpisodeProgressClick(episodeId: number, isFinished: boolean) {
    if (!isAuthenticated) {
      toast.info(t('subject.loginToTrackProgress'));
      return;
    }
    if (!userSubject) {
      toast.info(t('subject.markBeforeProgress'));
      return;
    }
    void handleEpisodeToggle(episodeId, isFinished);
  }

  if (!subjectId) {
    return (
      <Page title={t('subject.title')} eyebrow={t('subject.title')}>
        <EmptyState title={t('subject.missingTitle')} description={t('subject.missingBody')} />
      </Page>
    );
  }

  if (detailQuery.isLoading) {
    return (
      <Page title={t('subject.title')} eyebrow={t('subject.title')}>
        <LoadingState title={t('subject.loadingTitle')} />
      </Page>
    );
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <Page title={t('subject.title')} eyebrow={t('subject.title')}>
        <ErrorState title={t('subject.errorTitle')} description={t('subject.errorBody')} />
      </Page>
    );
  }

  const subject = detailQuery.data;
  const relationItems = relationsQuery.data?.results ?? [];
  const relationGroups = groupRelationsForDisplay(relationItems, t('subject.related'));
  const relationPages = paginateRelationGroups(relationGroups);
  const relationTotalPages = relationPages.length;
  const currentRelationPage = Math.min(relationPage, relationTotalPages);
  const visibleRelationGroups = relationPages[currentRelationPage - 1] ?? [];
  const relationRows = relationGroups.flatMap((group) => group.items);
  const episodeProgressIds = new Set(progress?.finished_episode_ids ?? []);
  const infoboxRows = sortInfoboxRows(getInfoboxRows(subject.infobox));
  const staffGroups = groupStaffByRole(staffQuery.data?.results ?? []);
  const staffRoleOptions = [
    { label: t('subject.allRoles'), value: '' },
    ...(staffRolesQuery.data?.roles ?? []).map((role) => ({ label: role, value: role })),
  ];
  const staffTotalPages = Math.max(1, Math.ceil((staffQuery.data?.count ?? 0) / staffPageSize));
  const episodeTotalPages = Math.max(1, Math.ceil((episodesQuery.data?.count ?? 0) / episodePageSize));
  const characterTotalPages = Math.max(1, Math.ceil((charactersQuery.data?.count ?? 0) / characterPageSize));
  const publicReviewTotalPages = Math.max(1, Math.ceil((publicReviewsQuery.data?.count ?? 0) / publicReviewPageSize));
  const episodeRows = episodesQuery.data?.results ?? progress?.episodes ?? [];
  const allOtherEpisodeRows = (otherEpisodesQuery.data?.results ?? []).filter((episode) => episode.type !== 'EP');
  const otherEpisodeTotalPages = Math.max(1, Math.ceil(allOtherEpisodeRows.length / otherEpisodePageSize));
  const otherEpisodeRows = allOtherEpisodeRows.slice(
    (otherEpisodePage - 1) * otherEpisodePageSize,
    otherEpisodePage * otherEpisodePageSize,
  );
  const finishedPrimaryCount =
    progress?.finished_count ?? episodeRows.filter((episode) => episodeProgressIds.has(episode.id)).length;
  const totalPrimaryCount = progress?.total_episodes ?? episodesQuery.data?.count ?? episodeRows.length;
  const selectedEpisodePreview = [...episodeRows, ...allOtherEpisodeRows].find(
    (episode) => episode.id === selectedEpisodeId,
  );
  const bangumiSnapshot = bangumiSnapshotQuery.data;
  const bangumiRank = bangumiSnapshot?.rating?.rank ?? bangumiSnapshot?.rank;
  const bangumiUrl = bangumiSubjectId ? `https://bangumi.tv/subject/${bangumiSubjectId}` : null;
  const anchorScrollClass = isAuthenticated ? 'scroll-mt-24' : 'scroll-mt-36';
  const detailLinkState = routeBackState(location, titleOf(subject, t('common.untitledSubject')));
  const loginState = { returnTo: currentRoutePath(location) };

  return (
    <Page
      title={titleOf(subject, t('common.untitledSubject'))}
      eyebrow={t('subject.title')}
      description={metaOf(subject)}
      seo={false}
      actions={
        <Button
          asChild
          aria-label={t('subject.graph')}
          className="graph-entry-button"
          size="icon"
          type="button"
          variant="secondary"
        >
          <Link title={t('subject.graph')} to={routes.subjectGraph(subject.id)}>
            <Network className="size-4" />
          </Link>
        </Button>
      }
    >
      <Seo
        title={titleOf(subject, t('common.untitledSubject'))}
        description={seoDescriptionOf(subject)}
        image={seoImageOf(subject)}
        path={routes.subject(subject.id)}
      />
      <nav className={`sticky ${isAuthenticated ? 'top-3' : 'top-20'} z-20 mb-5 flex justify-center`}>
        <div className="flex max-w-full gap-1 overflow-x-auto rounded-full border border-[var(--color-border)] bg-[color-mix(in_srgb,var(--color-surface)_92%,transparent)] p-1 text-sm shadow-sm backdrop-blur">
          {[
            ['#mark', t('subject.mark')],
            ['#reviews', t('reviews.title')],
            ['#episodes', t('subject.episodes')],
            ['#description', t('subject.description')],
            ['#characters', t('subject.characters')],
            ['#relations', t('subject.relations')],
            ['#public-reviews', t('subject.publicReviews')],
          ].map(([href, label]) => (
            <a
              className="whitespace-nowrap rounded-full px-3 py-1.5 font-semibold text-[var(--color-text-muted)] transition hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-text)]"
              href={href}
              key={href}
            >
              {label}
            </a>
          ))}
        </div>
      </nav>
      <div className="grid items-start gap-8 lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="grid content-start gap-4 self-start">
          <img
            className="aspect-[2/3] w-full rounded-xl bg-[var(--color-surface-muted)] object-cover shadow-sm ring-1 ring-[var(--color-border)]"
            src={posterOf(subject)}
            alt={titleOf(subject, t('common.untitledSubject'))}
          />

          {bangumiUrl ? (
            <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-normal text-[var(--color-text-muted)]">
                    {t('subject.externalSource')}
                  </p>
                  <h2 className="mt-1 flex min-w-0 items-center gap-2 text-sm font-semibold text-[var(--color-text)]">
                    <img
                      className="size-4 rounded-sm"
                      src="https://bangumi.tv/img/favicon.ico"
                      alt=""
                      aria-hidden="true"
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
                <div className="rounded-lg bg-[var(--color-surface-muted)] p-3">
                  <p className="text-[11px] font-semibold uppercase text-neutral-400">{t('subject.liveScore')}</p>
                  <p className="mt-1 text-base font-semibold text-[var(--color-text)]">
                    {bangumiSnapshot?.rating?.score ? bangumiSnapshot.rating.score.toFixed(1) : emptyText}
                  </p>
                </div>
                <div className="rounded-lg bg-[var(--color-surface-muted)] p-3">
                  <p className="text-[11px] font-semibold uppercase text-neutral-400">{t('subject.liveRank')}</p>
                  <p className="mt-1 text-base font-semibold text-[var(--color-text)]">
                    {bangumiRank ? `#${bangumiRank}` : emptyText}
                  </p>
                </div>
                <div className="rounded-lg bg-[var(--color-surface-muted)] p-3">
                  <p className="text-[11px] font-semibold uppercase text-neutral-400">{t('subject.liveVotes')}</p>
                  <p className="mt-1 text-base font-semibold text-[var(--color-text)]">
                    {bangumiSnapshot?.rating?.total ?? emptyText}
                  </p>
                </div>
              </div>
              {bangumiSnapshotQuery.isFetching ? (
                <p className="mt-3 text-xs text-[var(--color-text-muted)]">{t('subject.loadingExternalSource')}</p>
              ) : null}
              {bangumiSnapshotQuery.isError ? (
                <p className="mt-3 text-xs text-[var(--color-text-muted)]">{t('subject.externalSourceUnavailable')}</p>
              ) : null}
            </section>
          ) : null}

          <section className="border-t border-[var(--color-border)] pt-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold uppercase text-[var(--color-text-muted)]">{t('subject.infobox')}</h2>
              <span className="text-xs text-neutral-400">
                {infoboxRows.length} {t('common.items')}
              </span>
            </div>
            <dl className="mt-3 divide-y divide-[var(--color-border)] text-sm">
              {infoboxRows.slice(0, 14).map((item) => (
                <div className="grid grid-cols-[88px_minmax(0,1fr)] gap-3 py-2.5" key={item.key}>
                  <dt className="text-[var(--color-text-muted)]">{item.key}</dt>
                  <dd className="min-w-0 break-words leading-6 text-[var(--color-text)]">{item.value}</dd>
                </div>
              ))}
              {infoboxRows.length === 0 ? (
                <div className="py-3 text-sm text-[var(--color-text-muted)]">{emptyText}</div>
              ) : null}
            </dl>
          </section>

          <section className="border-t border-[var(--color-border)] pt-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold uppercase text-[var(--color-text-muted)]">{t('subject.staff')}</h2>
              <span className="text-xs text-neutral-400">
                {staffQuery.data?.count ?? 0} {t('common.items')}
              </span>
            </div>
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
                  <div className="text-xs font-semibold uppercase text-neutral-400">
                    {role === 'Staff' ? t('subject.staff') : role}
                  </div>
                  <div className="grid gap-2">
                    {members.map((member) => (
                      <Popover key={`${role}-${member.id}`}>
                        <PopoverTrigger asChild>
                          <button
                            className="grid grid-cols-[36px_minmax(0,1fr)] items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-2 text-left transition hover:border-[var(--color-accent-border)] hover:bg-[var(--color-surface-muted)] hover:shadow-sm"
                            type="button"
                          >
                            <img
                              className="size-9 rounded-md bg-[var(--color-surface-muted)] object-cover"
                              src={member.image_thumbnail || coverPlaceholder}
                              alt=""
                            />
                            <span className="min-w-0">
                              <span className="block truncate text-sm font-semibold text-[var(--color-text)]">
                                {member.name}
                              </span>
                              <span className="block truncate text-xs text-[var(--color-text-muted)]">
                                {member.type || (role === 'Staff' ? t('subject.staff') : role)}
                              </span>
                            </span>
                          </button>
                        </PopoverTrigger>
                        <PopoverContent
                          align="start"
                          className="max-h-[min(640px,calc(100dvh-2rem))] w-[min(420px,calc(100vw-2rem))] overflow-y-auto p-4"
                          side="right"
                        >
                          <StaffDetail
                            emptyLabel={emptyText}
                            labels={subjectDetailLabels}
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
                <p className="text-sm text-neutral-500 dark:text-neutral-400">{t('subject.loadingStaff')}</p>
              ) : null}
              {!staffQuery.isFetching && staffGroups.length === 0 ? (
                <p className="text-sm text-neutral-500 dark:text-neutral-400">{emptyText}</p>
              ) : null}
              <Pagination currentPage={staffPage} totalPages={staffTotalPages} onPageChange={setStaffPage} />
            </div>
          </section>
        </aside>

        <main className="grid gap-4 self-start">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card className={anchorScrollClass} id="mark">
              <CardHeader>
                <CardTitle>{t('subject.mark')}</CardTitle>
                {userSubject ? <CardDescription>{selectedStatusLabel}</CardDescription> : null}
              </CardHeader>
              <CardContent className="grid gap-4">
                {userSubject ? (
                  <div className="grid gap-3">
                    <div className="grid grid-cols-3 gap-2">
                      <div className="rounded-lg bg-[var(--color-surface-muted)] p-3">
                        <p className="text-xs font-semibold uppercase text-[var(--color-text-muted)]">
                          {t('subject.progress')}
                        </p>
                        <p className="mt-1 text-sm font-semibold text-[var(--color-text)]">
                          {finishedPrimaryCount} / {totalPrimaryCount}
                        </p>
                      </div>
                      <div className="rounded-lg bg-[var(--color-surface-muted)] p-3">
                        <p className="text-xs font-semibold uppercase text-[var(--color-text-muted)]">
                          {t('subject.simple')}
                        </p>
                        <p className="mt-1">
                          <StarRatingDisplay emptyLabel={emptyText} value={userSubject.simple_rating} />
                        </p>
                      </div>
                      <div className="rounded-lg bg-[var(--color-surface-muted)] p-3">
                        <p className="text-xs font-semibold uppercase text-[var(--color-text-muted)]">
                          {t('subject.rating')}
                        </p>
                        <p className="mt-1 text-sm font-semibold text-[var(--color-text)]">
                          {userSubject.rating ?? emptyText}
                        </p>
                      </div>
                    </div>
                    {(contextQuery.data?.tags ?? []).length ? (
                      <div className="flex flex-wrap gap-2">
                        {(contextQuery.data?.tags ?? []).map((tag) => (
                          <Badge key={tag.id} variant="secondary">
                            {tag.name}
                          </Badge>
                        ))}
                      </div>
                    ) : null}
                    {(contextQuery.data?.rating_details ?? []).length ? (
                      <dl className="grid gap-2 text-sm">
                        {(contextQuery.data?.rating_details ?? []).map((detail) => (
                          <div
                            className="flex items-center justify-between gap-3 rounded-lg border border-[var(--color-border)] px-3 py-2"
                            key={detail.key}
                          >
                            <dt className="truncate text-[var(--color-text-muted)]">{detail.key}</dt>
                            <dd className="font-semibold text-[var(--color-text)]">{detail.value}</dd>
                          </div>
                        ))}
                      </dl>
                    ) : null}
                    {userSubject.comment ? (
                      <p className="rounded-lg border border-[var(--color-border)] p-3 text-sm leading-6 text-[var(--color-text-muted)]">
                        {userSubject.comment}
                      </p>
                    ) : null}
                  </div>
                ) : (
                  <div className="mark-empty-panel">
                    <Star className="size-4" />
                    <span>{isAuthenticated ? t('subject.notMarked') : t('subject.loginToMark')}</span>
                  </div>
                )}
                {isAuthenticated ? (
                  <Button
                    className="mark-primary-action"
                    type="button"
                    variant="secondary"
                    onClick={() => setIsMarkDialogOpen(true)}
                  >
                    {userSubject ? <PencilLine className="size-4" /> : <Plus className="size-4" />}
                    {userSubject ? t('subject.editMark') : t('subject.markSubject')}
                  </Button>
                ) : (
                  <Button asChild className="mark-primary-action">
                    <Link state={loginState} to={routes.login}>
                      {t('auth.login')}
                    </Link>
                  </Button>
                )}
              </CardContent>
            </Card>

            <Card className={anchorScrollClass} id="reviews">
              <CardHeader>
                <CardTitle>{t('reviews.title')}</CardTitle>
                <CardDescription>
                  {(contextQuery.data?.reviews ?? []).length} {t('common.items')}
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3">
                {(contextQuery.data?.reviews ?? []).map((review) => (
                  <article className="rounded-lg border border-[var(--color-border)] p-3" key={review.id}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <Link
                          className="truncate text-sm font-semibold text-[var(--color-text)] transition hover:text-[var(--color-accent-strong)]"
                          state={detailLinkState}
                          to={routes.review(review.id)}
                        >
                          {review.title}
                        </Link>
                        <p className="mt-1 line-clamp-2 text-sm leading-6 text-[var(--color-text-muted)]">
                          {review.content}
                        </p>
                      </div>
                      <Button asChild size="icon" type="button" variant="ghost">
                        <Link state={detailLinkState} to={routes.reviewEdit(review.id)}>
                          <PencilLine className="size-4" />
                        </Link>
                      </Button>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Badge variant={review.is_public ? 'accent' : 'secondary'}>
                        {review.is_public ? t('common.public') : t('common.private')}
                      </Badge>
                      {review.is_spoiler ? (
                        <Badge>
                          <ShieldAlert className="size-3" /> {t('common.spoiler')}
                        </Badge>
                      ) : null}
                    </div>
                  </article>
                ))}
                {(contextQuery.data?.reviews ?? []).length === 0 ? (
                  <p className="text-sm leading-6 text-neutral-500 dark:text-neutral-400">{emptyText}</p>
                ) : null}
                {userSubject ? (
                  <Button asChild className="w-fit" variant="secondary">
                    <Link state={detailLinkState} to={routes.reviewNewForSubject(subjectId)}>
                      {t('subject.newReview')}
                    </Link>
                  </Button>
                ) : (
                  <Button className="w-fit" disabled type="button" variant="secondary">
                    {t('subject.newReview')}
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>

          <Card className={anchorScrollClass} id="episodes">
            <CardHeader>
              <CardTitle>{t('subject.episodes')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                {episodeRows.map((episode) => {
                  const checked = episodeProgressIds.has(episode.id);
                  const isEpisodePending = pendingEpisodeId === episode.id;
                  return (
                    <div
                      className={`episode-tile ${checked ? 'is-finished' : ''}`}
                      key={episode.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => setSelectedEpisodeId(episode.id)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          setSelectedEpisodeId(episode.id);
                        }
                      }}
                    >
                      <span className="episode-tile-topline">
                        <span className="episode-tile-label">{episodeLabel(episode)}</span>
                        <button
                          className={`episode-progress-button ${checked ? 'is-finished' : ''}`}
                          disabled={isEpisodePending}
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            handleEpisodeProgressClick(episode.id, !checked);
                          }}
                        >
                          {checked ? <Check className="size-3" /> : null}
                          {isEpisodePending
                            ? t('common.saving')
                            : checked
                              ? t('subject.watched')
                              : t('subject.markWatched')}
                        </button>
                      </span>
                      <span className="episode-tile-title">{episodeTitle(episode)}</span>
                      <span className="episode-tile-meta">
                        <span className="truncate">{episodeMeta(episode, emptyText)}</span>
                        <span className="font-semibold text-[var(--color-accent-strong)]">{episode.type}</span>
                      </span>
                    </div>
                  );
                })}
                {!episodesQuery.isFetching && episodeRows.length === 0 ? (
                  <p className="text-sm text-neutral-500 dark:text-neutral-400">{emptyText}</p>
                ) : null}
              </div>
              <Pagination currentPage={episodePage} totalPages={episodeTotalPages} onPageChange={setEpisodePage} />
              {otherEpisodeRows.length > 0 ? (
                <div className="mt-5 border-t border-[var(--color-border)] pt-4">
                  <h3 className="text-sm font-semibold text-[var(--color-text)]">{t('subject.otherChapters')}</h3>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {otherEpisodeRows.map((episode) => (
                      <button
                        className="other-chapter-tile"
                        key={episode.id}
                        type="button"
                        onClick={() => setSelectedEpisodeId(episode.id)}
                      >
                        <span className="other-chapter-type">{episode.type}</span>
                        <span className="min-w-0">
                          <span className="other-chapter-title">{episodeTitle(episode)}</span>
                          <span className="other-chapter-meta">
                            {episodeLabel(episode)} · {episodeMeta(episode, emptyText)}
                          </span>
                        </span>
                      </button>
                    ))}
                  </div>
                  <Pagination
                    currentPage={otherEpisodePage}
                    totalPages={otherEpisodeTotalPages}
                    onPageChange={setOtherEpisodePage}
                  />
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card className={anchorScrollClass} id="description">
            <CardHeader>
              <CardTitle>{t('subject.description')}</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4">
              <p className="text-sm leading-7 text-neutral-600 dark:text-neutral-300">
                {subject.description || subject.summary || emptyText}
              </p>
              {subject.tags?.length ? (
                <div className="flex flex-wrap gap-2">
                  {subject.tags.slice(0, 12).map((tag) => (
                    <span
                      className="rounded-full bg-[var(--color-surface-muted)] px-3 py-1 text-xs font-semibold text-[var(--color-text-muted)]"
                      key={tag}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card className={anchorScrollClass} id="characters">
            <CardHeader>
              <CardTitle>{t('subject.characters')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2">
                {(charactersQuery.data?.results ?? []).map((character) => (
                  <button
                    className="grid grid-cols-[56px_minmax(0,1fr)] gap-3 rounded-lg border border-[var(--color-border)] p-3 text-left transition hover:border-[var(--color-accent-border)] hover:bg-[var(--color-surface-muted)] hover:shadow-sm"
                    key={character.id}
                    type="button"
                    onClick={() => setSelectedCharacter(character)}
                  >
                    <img
                      className="h-20 w-14 rounded-md bg-[var(--color-surface-muted)] object-cover object-top"
                      src={character.image_thumbnail || coverPlaceholder}
                      alt={character.name}
                    />
                    <div className="min-w-0">
                      <h3 className="truncate text-sm font-semibold text-[var(--color-text)]">{character.name}</h3>
                      <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                        {character.role || character.type || t('subject.character')}
                      </p>
                      <div className="mt-3 grid gap-1">
                        {(character.actors ?? []).slice(0, 2).map((actor) => (
                          <div className="grid grid-cols-[24px_minmax(0,1fr)] items-center gap-2" key={actor.id}>
                            <img
                              className="size-6 rounded-full bg-[var(--color-surface-muted)] object-cover object-top"
                              src={actor.image_thumbnail || coverPlaceholder}
                              alt=""
                            />
                            <span className="truncate text-xs text-neutral-600 dark:text-neutral-300">
                              {actor.name}
                            </span>
                          </div>
                        ))}
                        {(character.actors ?? []).length === 0 ? (
                          <span className="text-xs text-neutral-400">{emptyText}</span>
                        ) : null}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
              <Pagination
                currentPage={characterPage}
                totalPages={characterTotalPages}
                onPageChange={setCharacterPage}
              />
            </CardContent>
          </Card>

          <Card className={anchorScrollClass} id="relations">
            <CardContent className="grid gap-5 pt-6">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold tracking-tight text-neutral-950 dark:text-white">
                    {t('subject.relations')}
                  </h2>
                  <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                    {relationsQuery.isFetching && relationRows.length === 0
                      ? t('subject.loadingRelatedSubjects')
                      : `${relationsQuery.data?.count ?? 0} ${t('subject.relatedSubjects')}`}
                  </p>
                </div>
              </div>

              {relationsQuery.isFetching && relationRows.length === 0 ? (
                <LoadingState title={t('subject.loadingRelations')} description={t('subject.loadingRelationsBody')} />
              ) : null}

              {relationsQuery.isError ? (
                <div className="grid gap-3">
                  <ErrorState title={t('subject.relationsErrorTitle')} description={t('subject.relationsErrorBody')} />
                  <Button
                    className="w-fit"
                    type="button"
                    variant="secondary"
                    onClick={() => void relationsQuery.refetch()}
                  >
                    {t('common.retry')}
                  </Button>
                </div>
              ) : null}

              {!relationsQuery.isFetching && !relationsQuery.isError && relationRows.length === 0 ? (
                <p className="text-sm text-neutral-500 dark:text-neutral-400">{emptyText}</p>
              ) : null}

              {relationRows.length > 0 ? (
                <div className="relation-groups">
                  {visibleRelationGroups.map((group) => (
                    <section className="relation-section" key={group.key}>
                      <div className="relation-section-heading">
                        <span>{group.label}</span>
                        <small>
                          {group.items.length === group.totalCount
                            ? group.items.length
                            : `${group.items.length}/${group.totalCount}`}
                        </small>
                      </div>
                      <div className="relation-grid">
                        {group.items.map((relation) => {
                          const primary = isPrimaryRelation(relation);
                          const content = (
                            <RelationItemContent
                              emptyText={emptyText}
                              relation={relation}
                              titleFallback={t('common.untitledSubject')}
                            />
                          );

                          return primary ? (
                            <Link
                              className="relation-item"
                              key={`${relation.direction}-${relation.relation}-${relation.subject.id}`}
                              state={detailLinkState}
                              to={routes.subject(relation.subject.id)}
                            >
                              {content}
                            </Link>
                          ) : (
                            <button
                              className="relation-item w-full text-left"
                              key={`${relation.direction}-${relation.relation}-${relation.subject.id}`}
                              type="button"
                              onClick={() => setSelectedRelation(relation)}
                            >
                              {content}
                            </button>
                          );
                        })}
                      </div>
                    </section>
                  ))}
                </div>
              ) : null}

              <Pagination
                currentPage={currentRelationPage}
                totalPages={relationTotalPages}
                onPageChange={setRelationPage}
              />
            </CardContent>
          </Card>

          <Card className={anchorScrollClass} id="public-reviews">
            <CardContent className="grid gap-4 pt-6">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold tracking-tight text-neutral-950 dark:text-white">
                    {t('subject.publicReviews')}
                  </h2>
                  <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                    {publicReviewsQuery.data?.count ?? 0} {t('subject.publicReviews')}
                  </p>
                </div>
              </div>
              <div className="mt-4 divide-y divide-neutral-200 dark:divide-neutral-800">
                {(publicReviewsQuery.data?.results ?? []).map((review) => {
                  const isOwnReview = Boolean(
                    review.user?.id && auth.profile?.user_id && String(review.user.id) === String(auth.profile.user_id),
                  );
                  return (
                    <article className="py-5 first:pt-0 last:pb-0" key={review.id}>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex min-w-0 items-center gap-3">
                          {review.user?.id ? (
                            <Link to={routes.userProfile(review.user.id)}>
                              <img
                                alt=""
                                className="size-9 rounded-full bg-[var(--color-surface-muted)] object-cover transition hover:ring-2 hover:ring-[var(--color-accent-border)]"
                                src={review.user.avatar || '/assets/placeholders/avatar.png'}
                              />
                            </Link>
                          ) : (
                            <img
                              alt=""
                              className="size-9 rounded-full bg-[var(--color-surface-muted)] object-cover"
                              src="/assets/placeholders/avatar.png"
                            />
                          )}
                          <div className="min-w-0">
                            {review.user?.id ? (
                              <Link
                                className="block truncate text-sm font-semibold text-[var(--color-text)] transition hover:text-[var(--color-accent-strong)]"
                                to={routes.userProfile(review.user.id)}
                              >
                                {review.user.nickname || t('common.anonymous')}
                              </Link>
                            ) : (
                              <p className="truncate text-sm font-semibold text-[var(--color-text)]">
                                {t('common.anonymous')}
                              </p>
                            )}
                            <p className="text-xs text-neutral-500 dark:text-neutral-400">
                              {formatDate(review.updated_at || review.created_at)}
                            </p>
                          </div>
                        </div>
                        <div className="flex flex-shrink-0 flex-wrap justify-end gap-2">
                          {review.is_spoiler ? (
                            <Badge>
                              <ShieldAlert className="size-3" /> {t('common.spoiler')}
                            </Badge>
                          ) : null}
                          {isOwnReview ? (
                            <Button asChild size="sm" variant="ghost">
                              <Link state={detailLinkState} to={routes.reviewEdit(review.id)}>
                                {t('common.edit')}
                              </Link>
                            </Button>
                          ) : null}
                        </div>
                      </div>
                      <Link className="mt-4 block" state={detailLinkState} to={routes.review(review.id)}>
                        <h3 className="font-semibold text-[var(--color-text)] transition hover:text-[var(--color-accent-strong)]">
                          {review.title}
                        </h3>
                        <div
                          className={`relative mt-2 overflow-hidden rounded-lg ${review.is_spoiler ? 'max-h-24' : ''}`}
                        >
                          <p
                            className={`line-clamp-3 text-sm leading-6 text-neutral-600 dark:text-neutral-300 ${review.is_spoiler ? 'blur-sm transition hover:blur-none' : ''}`}
                          >
                            {review.content}
                          </p>
                          {review.is_spoiler ? (
                            <div className="pointer-events-none absolute inset-0 grid place-items-center bg-[color-mix(in_srgb,var(--color-surface)_38%,transparent)] text-xs font-semibold text-[var(--color-text)] backdrop-blur-sm">
                              {t('subject.spoilerReview')}
                            </div>
                          ) : null}
                        </div>
                      </Link>
                    </article>
                  );
                })}
                {!publicReviewsQuery.isFetching && (publicReviewsQuery.data?.results.length ?? 0) === 0 ? (
                  <p className="text-sm text-neutral-500 dark:text-neutral-400">{emptyText}</p>
                ) : null}
              </div>
              <Pagination
                currentPage={publicReviewPage}
                totalPages={publicReviewTotalPages}
                onPageChange={setPublicReviewPage}
              />
            </CardContent>
          </Card>
        </main>
      </div>
      <Dialog open={isMarkDialogOpen} onOpenChange={setIsMarkDialogOpen}>
        <DialogContent className="grid max-h-[calc(100dvh-2rem)] max-w-3xl grid-rows-[auto_minmax(0,1fr)_auto] gap-0 overflow-hidden p-0">
          <DialogHeader className="border-b border-[var(--color-border)] px-5 py-4 pr-12">
            <DialogTitle>{userSubject ? t('subject.editMark') : t('subject.markSubject')}</DialogTitle>
          </DialogHeader>
          <div className="min-h-0 overflow-y-auto px-5 py-5">
            <form className="grid gap-5" id="subject-mark-form" onSubmit={(event) => void handleMarkSubmit(event)}>
              <section className="grid gap-3">
                <div>
                  <div className="text-sm font-semibold text-[var(--color-text)]">{t('subject.status')}</div>
                </div>
                <div className="grid gap-2 sm:grid-cols-5">
                  {statusOptions.map((option) => {
                    const selected = status === option.value;
                    const StatusIcon = statusStyles[option.value]?.icon ?? Sparkles;
                    const tone = statusStyles[option.value]?.tone ?? 'status-wish';
                    return (
                      <button
                        className={`mark-status-option ${tone} ${selected ? 'is-selected' : ''}`}
                        key={option.value}
                        type="button"
                        onClick={() => setStatus(option.value)}
                      >
                        <span className="mark-status-icon">
                          <StatusIcon className="size-4" />
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate">{option.label}</span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              </section>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="grid gap-2 text-sm font-medium text-[var(--color-text)]">
                  {t('subject.simple')}
                  <StarRatingControl clearLabel={t('common.clear')} value={simpleRating} onChange={setSimpleRating} />
                </label>
                <label className="grid gap-2 text-sm font-medium text-[var(--color-text)]">
                  {t('subject.rating')}
                  <Input
                    inputMode="decimal"
                    placeholder="0.0 - 10.0"
                    value={rating}
                    onChange={(event) => setRating(event.target.value)}
                  />
                </label>
              </div>
              <label className="grid gap-2 text-sm font-medium text-[var(--color-text)]">
                {t('subject.comment')}
                <textarea
                  className="min-h-24 rounded-xl border-0 bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] shadow-sm outline-none ring-1 ring-[var(--color-border)] focus:ring-4 focus:ring-[var(--color-focus-ring)]"
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                />
              </label>
              <div className="mark-visibility-toggle">
                <span className="grid min-w-0 gap-0.5">
                  <span className="font-semibold text-[var(--color-text)]">{t('subject.publicVisibility')}</span>
                </span>
                <button
                  aria-pressed={isPublic}
                  className={`mark-switch ${isPublic ? 'is-on' : ''}`}
                  type="button"
                  onClick={() => setIsPublic((value) => !value)}
                >
                  <span />
                </button>
              </div>
              <section className="grid gap-3 border-t border-[var(--color-border)] pt-5">
                <label className="grid gap-2 text-sm font-medium text-[var(--color-text)]">
                  {t('subject.tags')}
                  <Input
                    placeholder="favorite, rewatch, key"
                    value={tagText}
                    onChange={(event) => setTagText(event.target.value)}
                  />
                </label>
                <div className="flex flex-wrap gap-2">
                  {(tagsQuery.data?.results ?? []).slice(0, 8).map((tag) => (
                    <button
                      className="rounded-full border border-[var(--color-border)] px-3 py-1 text-xs font-semibold text-[var(--color-text-muted)] transition hover:border-[var(--color-accent-border)] hover:text-[var(--color-accent-strong)]"
                      key={tag.id}
                      type="button"
                      onClick={() => {
                        const tags = tagText
                          .split(',')
                          .map((item) => item.trim())
                          .filter(Boolean);
                        if (!tags.includes(tag.name)) {
                          setTagText([...tags, tag.name].join(', '));
                        }
                      }}
                    >
                      {tag.name}
                    </button>
                  ))}
                </div>
              </section>
              <section className="grid gap-3 border-t border-[var(--color-border)] pt-5">
                <div>
                  <div className="text-sm font-semibold text-[var(--color-text)]">{t('subject.ratingDetails')}</div>
                </div>
                <div className="grid gap-2">
                  {ratingDetailRows.map((detail, index) => (
                    <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_40px]" key={index}>
                      <Input
                        placeholder="key"
                        value={detail.key}
                        onChange={(event) =>
                          setRatingDetailRows((rows) =>
                            rows.map((row, rowIndex) =>
                              rowIndex === index ? { ...row, key: event.target.value } : row,
                            ),
                          )
                        }
                      />
                      <Input
                        placeholder="value"
                        value={detail.value}
                        onChange={(event) =>
                          setRatingDetailRows((rows) =>
                            rows.map((row, rowIndex) =>
                              rowIndex === index ? { ...row, value: event.target.value } : row,
                            ),
                          )
                        }
                      />
                      <Button
                        disabled={ratingDetailRows.length <= 1}
                        size="icon"
                        type="button"
                        variant="secondary"
                        onClick={() => setRatingDetailRows((rows) => rows.filter((_, rowIndex) => rowIndex !== index))}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => setRatingDetailRows((rows) => [...rows, { key: '', value: '' }])}
                  >
                    <Plus className="size-4" />
                    {t('subject.addDetail')}
                  </Button>
                </div>
              </section>
              {noticeMessage ? (
                <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
                  {noticeMessage}
                </p>
              ) : null}
              {errorMessage ? (
                <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-300">
                  {errorMessage}
                </p>
              ) : null}
            </form>
          </div>
          <div className={`mark-dialog-footer ${userSubject ? '' : 'is-single'}`}>
            <Button
              className="mark-dialog-submit"
              disabled={
                createSubjectMutation.isPending ||
                updateSubjectMutation.isPending ||
                replaceTagsMutation.isPending ||
                replaceRatingDetailsMutation.isPending
              }
              form="subject-mark-form"
              type="submit"
            >
              <Check className="size-4" />
              {userSubject ? t('subject.saveMark') : t('subject.markSubject')}
            </Button>
            {userSubject ? (
              <Button
                className="mark-dialog-delete"
                disabled={deleteSubjectMutation.isPending}
                type="button"
                variant="secondary"
                onClick={() => setIsDeleteConfirmOpen(true)}
              >
                <Trash2 className="size-4" />
                {t('subject.deleteMark')}
              </Button>
            ) : null}
          </div>
        </DialogContent>
      </Dialog>
      <Dialog open={isDeleteConfirmOpen} onOpenChange={setIsDeleteConfirmOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t('subject.deleteMarkTitle')}</DialogTitle>
            <DialogDescription>{t('subject.deleteMarkBody')}</DialogDescription>
          </DialogHeader>
          <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-300">
            <AlertTriangle className="mr-2 inline size-4" />
            {t('subject.deleteMarkWarning')}
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setIsDeleteConfirmOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button disabled={deleteSubjectMutation.isPending} type="button" onClick={() => void handleDeleteMark()}>
              {t('common.delete')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
      <Dialog open={selectedEpisodeId !== null} onOpenChange={(open) => !open && setSelectedEpisodeId(null)}>
        <DialogContent className="max-w-lg">
          {selectedEpisodeQuery.isLoading && !selectedEpisodePreview ? (
            <LoadingState title={t('subject.loadingEpisode')} />
          ) : selectedEpisodeQuery.isError ? (
            <ErrorState title={t('subject.episodeErrorTitle')} />
          ) : selectedEpisodeQuery.data || selectedEpisodePreview ? (
            <>
              <DialogHeader>
                <DialogTitle>{episodeTitle(selectedEpisodeQuery.data ?? selectedEpisodePreview!)}</DialogTitle>
                <DialogDescription>
                  {[
                    episodeLabel(selectedEpisodeQuery.data ?? selectedEpisodePreview!),
                    (selectedEpisodeQuery.data ?? selectedEpisodePreview!).type,
                    (selectedEpisodeQuery.data ?? selectedEpisodePreview!).date,
                  ]
                    .filter(Boolean)
                    .join(' · ') || t('subject.episodeDetail')}
                </DialogDescription>
              </DialogHeader>
              <DetailShell
                image={posterOf(subject)}
                title={episodeTitle(selectedEpisodeQuery.data ?? selectedEpisodePreview!)}
                subtitle={episodeLabel(selectedEpisodeQuery.data ?? selectedEpisodePreview!)}
                description={(selectedEpisodeQuery.data ?? selectedEpisodePreview!).description}
                emptyLabel={emptyText}
                rows={detailRows([
                  [t('subject.type'), (selectedEpisodeQuery.data ?? selectedEpisodePreview!).type],
                  [t('subject.episode'), (selectedEpisodeQuery.data ?? selectedEpisodePreview!).ep_num],
                  [t('subject.sort'), (selectedEpisodeQuery.data ?? selectedEpisodePreview!).sort],
                  [t('subject.date'), (selectedEpisodeQuery.data ?? selectedEpisodePreview!).date],
                  [t('subject.duration'), (selectedEpisodeQuery.data ?? selectedEpisodePreview!).duration],
                ])}
              />
            </>
          ) : (
            <EmptyState title={emptyText} />
          )}
        </DialogContent>
      </Dialog>
      <Dialog open={Boolean(selectedCharacter)} onOpenChange={(open) => !open && setSelectedCharacter(null)}>
        <DialogContent className="max-h-[calc(100dvh-2rem)] max-w-2xl overflow-y-auto">
          {selectedCharacter ? (
            <>
              <DialogHeader>
                <DialogTitle>{selectedCharacter.name}</DialogTitle>
                <DialogDescription>
                  {[selectedCharacter.role, selectedCharacter.type].filter(Boolean).join(' · ') ||
                    t('subject.characterDetail')}
                </DialogDescription>
              </DialogHeader>
              <DetailShell
                image={selectedCharacter.image_original || selectedCharacter.image_thumbnail}
                title={selectedCharacter.name}
                subtitle={[selectedCharacter.role, selectedCharacter.type].filter(Boolean).join(' · ')}
                description={selectedCharacter.description}
                emptyLabel={emptyText}
                rows={[
                  ...detailRows([
                    [t('subject.gender'), selectedCharacter.gender],
                    [t('subject.birth'), selectedCharacter.birth],
                    [t('subject.bloodType'), selectedCharacter.blood_type],
                  ]),
                  ...getInfoboxRows(selectedCharacter.infobox)
                    .slice(0, 8)
                    .map((item) => [item.key, item.value] as const),
                ]}
              >
                {(selectedCharacter.actors ?? []).length ? (
                  <section className="grid gap-3">
                    <h4 className="text-sm font-semibold text-[var(--color-text)]">{t('subject.voiceCast')}</h4>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {(selectedCharacter.actors ?? []).map((actor) => (
                        <button
                          className="grid grid-cols-[40px_minmax(0,1fr)] items-center gap-3 rounded-lg border border-[var(--color-border)] p-2 text-left transition hover:border-[var(--color-accent-border)] hover:bg-[var(--color-surface-muted)] hover:shadow-sm"
                          key={actor.id}
                          type="button"
                          onClick={() => setSelectedStaff(actor)}
                        >
                          <img
                            alt=""
                            className="size-10 rounded-md bg-[var(--color-surface-muted)] object-cover object-top"
                            src={actor.image_thumbnail || coverPlaceholder}
                          />
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-[var(--color-text)]">{actor.name}</p>
                            <p className="truncate text-xs text-neutral-500 dark:text-neutral-400">
                              {actor.type || t('subject.voice')}
                            </p>
                          </div>
                        </button>
                      ))}
                    </div>
                  </section>
                ) : null}
              </DetailShell>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
      <Dialog open={Boolean(selectedStaff)} onOpenChange={(open) => !open && setSelectedStaff(null)}>
        <DialogContent className="max-h-[calc(100dvh-2rem)] max-w-2xl overflow-y-auto">
          {selectedStaff ? (
            <>
              <DialogHeader>
                <DialogTitle>{selectedStaff.name}</DialogTitle>
                <DialogDescription>
                  {selectedStaff.role || selectedStaff.type || t('subject.staffDetail')}
                </DialogDescription>
              </DialogHeader>
              <StaffDetail emptyLabel={emptyText} labels={subjectDetailLabels} staff={selectedStaff} />
            </>
          ) : null}
        </DialogContent>
      </Dialog>
      <Dialog open={Boolean(selectedRelation)} onOpenChange={(open) => !open && setSelectedRelation(null)}>
        <DialogContent className="max-h-[calc(100dvh-2rem)] max-w-2xl overflow-y-auto">
          {selectedRelation ? (
            <>
              <DialogHeader>
                <DialogTitle>{relationTitle(selectedRelation, t('common.untitledSubject'))}</DialogTitle>
                <DialogDescription>
                  {[selectedRelation.subject.subject_type, selectedRelation.relation || t('subject.related')]
                    .filter(Boolean)
                    .join(' · ')}
                </DialogDescription>
              </DialogHeader>
              <DetailShell
                image={selectedRelation.subject.image_original || selectedRelation.subject.image_thumbnail}
                title={relationTitle(selectedRelation, t('common.untitledSubject'))}
                subtitle={[selectedRelation.relation || t('subject.related'), selectedRelation.subject.subject_type]
                  .filter(Boolean)
                  .join(' · ')}
                description={selectedRelation.subject.description}
                emptyLabel={emptyText}
                rows={detailRows([
                  [t('subject.type'), selectedRelation.subject.subject_type],
                  [t('subject.relation'), selectedRelation.relation],
                  [t('subject.direction'), selectedRelation.direction],
                  [t('subject.date'), selectedRelation.subject.date],
                  [t('subject.platform'), selectedRelation.subject.platform],
                ])}
              />
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </Page>
  );
}
