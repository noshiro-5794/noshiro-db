import { useId } from 'react';
import ReactMarkdown from 'react-markdown';
import type { SubjectDetail } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { Badge } from '@/shared/ui/Badge';
import { DetailSection } from '@/shared/ui/Detail';

export function SubjectDescriptionSection({ className, subject }: { className?: string; subject: SubjectDetail }) {
  const { locale, t } = useI18n();
  const titleId = useId();
  // Descriptions arrive in every language a provider published. Prefer the one
  // matching the interface, then the canonical one, so a Chinese reader does
  // not land on the English synopsis while a translation exists.
  const primaryLanguage = locale.slice(0, 2).toLowerCase();
  const localized = subject.descriptions.find(
    (description) => description.text && description.language.toLowerCase().startsWith(primaryLanguage),
  );
  const selected = localized ?? subject.descriptions[0];
  const text = selected?.text || subject.description || subject.summary;
  const formatted = selected?.is_machine_generated && selected.is_reviewed && Boolean(text);

  return (
    <DetailSection className={className} id="description" title={t('subject.description')} titleId={titleId}>
      {formatted ? (
        <div className="max-w-3xl space-y-3 text-sm leading-7 text-muted-foreground [&_ol]:list-decimal [&_ul]:list-disc [&_li]:ml-5 [&_h3]:font-semibold [&_h4]:font-semibold">
          <ReactMarkdown
            skipHtml
            allowedElements={['p', 'em', 'strong', 'ul', 'ol', 'li', 'br', 'blockquote', 'h3', 'h4']}
            unwrapDisallowed
          >
            {text ?? ''}
          </ReactMarkdown>
        </div>
      ) : (
        <p className="m-0 max-w-3xl whitespace-pre-line text-sm leading-7 text-muted-foreground">
          {text || t('common.notRecorded')}
        </p>
      )}
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
