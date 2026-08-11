import { useId } from 'react';
import type { SubjectDetail } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { Badge } from '@/shared/ui/Badge';
import { DetailSection } from '@/shared/ui/Detail';

export function SubjectDescriptionSection({ className, subject }: { className?: string; subject: SubjectDetail }) {
  const { t } = useI18n();
  const titleId = useId();

  return (
    <DetailSection className={className} id="description" title={t('subject.description')} titleId={titleId}>
      <p className="m-0 whitespace-pre-line text-sm leading-7 text-muted-foreground">
        {subject.description || subject.summary || t('common.none')}
      </p>
      {subject.tags?.length ? (
        <div className="flex flex-wrap gap-1.5">
          {subject.tags.slice(0, 12).map((tag) => (
            <Badge key={tag}>{tag}</Badge>
          ))}
        </div>
      ) : null}
    </DetailSection>
  );
}
