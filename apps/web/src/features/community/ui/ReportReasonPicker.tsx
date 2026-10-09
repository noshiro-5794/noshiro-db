import { useId } from 'react';
import type { CommunityReportReason } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { Toggle, ToggleGroup } from '@/shared/ui/Toggle';

const reportReasons = ['spam', 'harassment', 'spoiler', 'illegal', 'other'] as const satisfies CommunityReportReason[];

type ReportReasonPickerProps = {
  value: CommunityReportReason;
  onValueChange: (value: CommunityReportReason) => void;
};

export function ReportReasonPicker({ value, onValueChange }: ReportReasonPickerProps) {
  const { t } = useI18n();
  const labelId = useId();

  return (
    <div className="grid gap-2">
      <span className="text-sm font-semibold text-[var(--ui-text)]" id={labelId}>
        {t('community.reportReason')}
      </span>
      <ToggleGroup
        aria-labelledby={labelId}
        className="flex w-full flex-wrap"
        value={[value]}
        onValueChange={(values) => {
          const nextValue = values[0];
          if (nextValue) onValueChange(nextValue);
        }}
      >
        {reportReasons.map((reason) => (
          <Toggle key={reason} value={reason}>
            {t(`community.reportReason.${reason}`)}
          </Toggle>
        ))}
      </ToggleGroup>
    </div>
  );
}
