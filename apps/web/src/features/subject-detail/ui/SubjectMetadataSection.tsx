import { useId } from 'react';
import { useI18n } from '@/shared/i18n';
import { DetailSection } from '@/shared/ui/Detail';
import { attributeLabelKeys, attributeValueKey, type SubjectAttribute } from '../model/subject-detail';

const groups = {
  work: 'subject.metadataWork',
  production: 'subject.metadataProduction',
  editions: 'subject.metadataEditions',
  references: 'subject.metadataReferences',
} as const;

const referenceKeys = new Set(['alternative-titles', 'website', 'hashtag', 'infobox:copyright']);
const editionKeys = new Set([
  'platform',
  'platforms',
  'languages',
  'original-language',
  'estimated-length',
  'game-engine',
  'players',
  'publisher',
  'infobox:translation editions',
  'infobox:售价',
  'infobox:其他版本',
]);
const productionKeys = new Set(['animation-production', 'developer', 'producers']);

function groupOf(key: string): keyof typeof groups {
  if (referenceKeys.has(key)) return 'references';
  if (editionKeys.has(key)) return 'editions';
  if (productionKeys.has(key) || key.startsWith('infobox:')) return 'production';
  return 'work';
}

export function SubjectMetadataSection({
  attributes,
  className,
}: {
  attributes: SubjectAttribute[];
  className?: string;
}) {
  const { t } = useI18n();
  const titleId = useId();
  const grouped: Record<keyof typeof groups, SubjectAttribute[]> = {
    work: [],
    production: [],
    editions: [],
    references: [],
  };
  for (const item of attributes) grouped[groupOf(item.key)].push(item);

  return (
    <DetailSection className={className} id="work-metadata" title={t('subject.info')} titleId={titleId}>
      <div className="grid min-w-0 gap-6">
        {(Object.keys(groups) as Array<keyof typeof groups>).map((group) => {
          const fields = grouped[group];
          if (fields.length === 0) return null;

          return (
            <div className="grid min-w-0 gap-2.5" data-metadata-group={group} key={group}>
              <h3 className="m-0 text-sm font-semibold text-foreground">{t(groups[group])}</h3>
              <dl className="m-0 grid min-w-0 border-y border-border-subtle sm:grid-cols-2 sm:gap-x-5">
                {fields.map((item) => {
                  const label = attributeLabelKeys[item.key];
                  const translated = attributeValueKey(item.key, item.value);
                  const value = item.key === 'type' || item.key === 'format' ? item.value.toUpperCase() : item.value;
                  const wide = item.value.includes('\n') || item.value.length > 100;
                  return (
                    <div
                      className={`grid min-w-0 grid-cols-[minmax(6rem,30%)_minmax(0,1fr)] gap-3 border-b border-border-subtle px-1 py-2.5 text-sm last:border-b-0 ${wide ? 'sm:col-span-2' : ''}`}
                      data-metadata-field={item.key}
                      key={item.key}
                    >
                      <dt className="min-w-0 break-words leading-6 text-muted-foreground">
                        {label ? t(label) : item.label || item.key}
                      </dt>
                      <dd className="m-0 min-w-0 whitespace-pre-line leading-6 text-foreground [overflow-wrap:anywhere]">
                        {translated ? t(translated) : value}
                      </dd>
                    </div>
                  );
                })}
              </dl>
            </div>
          );
        })}
      </div>
    </DetailSection>
  );
}
