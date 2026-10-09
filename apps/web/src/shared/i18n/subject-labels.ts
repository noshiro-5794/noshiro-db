import type { useI18n } from './use-i18n';
import type { MessageKey } from './catalog';

type Translate = ReturnType<typeof useI18n>['t'];

const statusKeys = {
  wish: 'status.wish',
  doing: 'status.doing',
  done: 'status.done',
  on_hold: 'status.onHold',
  drop: 'status.drop',
} as const;

/**
 * Reader-facing label for a library status. The API stores slugs (`on_hold`),
 * which used to reach cards as "anime / on hold".
 */
export function subjectStatusLabel(status: string | null | undefined, t: Translate): string {
  if (!status) return t('status.marked');
  const key = (statusKeys as Record<string, MessageKey | undefined>)[status];
  return key === undefined ? status.replaceAll('_', ' ') : t(key);
}

/** Reader-facing label for a catalogue bucket: anime -> 动画, galgame -> Galgame. */
export function subjectKindLabel(kind: string | null | undefined, t: Translate): string {
  if (kind === 'anime') return t('search.anime');
  if (kind === 'galgame') return t('search.galgame');
  return kind || '';
}
