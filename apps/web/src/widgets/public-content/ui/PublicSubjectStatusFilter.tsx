import { SlidersHorizontal } from 'lucide-react';
import type { UserSubjectStatus } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { FilterPanel, FilterPanelChoice, FilterPanelHeader } from '@/shared/ui/FilterPanel';
import { ToggleGroup } from '@/shared/ui/Toggle';

export function PublicSubjectStatusFilter({
  status,
  onChange,
}: {
  status: string;
  onChange: (status: string) => void;
}) {
  const { t } = useI18n();
  const options: Array<{ label: string; value: UserSubjectStatus | '' }> = [
    { label: t('status.all'), value: '' },
    { label: t('status.wish'), value: 'wish' },
    { label: t('status.doing'), value: 'doing' },
    { label: t('status.done'), value: 'done' },
    { label: t('status.onHold'), value: 'on_hold' },
    { label: t('status.drop'), value: 'drop' },
  ];

  return (
    <aside className="grid content-start gap-4">
      <FilterPanel>
        <FilterPanelHeader>
          <SlidersHorizontal className="size-4 text-[var(--ui-text-subtle)]" />
          <h2>{t('library.status')}</h2>
        </FilterPanelHeader>
        <ToggleGroup
          aria-label={t('library.status')}
          className="grid gap-1 border-0 bg-transparent p-0"
          orientation="vertical"
          value={[status || 'all']}
          onValueChange={(values) => {
            const nextStatus = values[0];
            if (nextStatus) onChange(nextStatus === 'all' ? '' : nextStatus);
          }}
        >
          {options.map((option) => (
            <FilterPanelChoice key={option.value || 'all'} value={option.value || 'all'}>
              <span>{option.label}</span>
            </FilterPanelChoice>
          ))}
        </ToggleGroup>
      </FilterPanel>
    </aside>
  );
}
