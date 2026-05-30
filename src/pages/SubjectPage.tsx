import { useParams } from 'react-router-dom';
import { useI18n } from '@/features/i18n/use-i18n';
import { Page } from '@/shared/ui/Page';

export function SubjectPage() {
  const { t } = useI18n();
  const { subjectId } = useParams();

  return (
    <Page title={t('subject.title')}>
      <p>{subjectId ? `Subject ID: ${subjectId}` : '未提供 subjectId'}</p>
    </Page>
  );
}
