import { Monitor, Moon, Sun } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import type { ThemePreference } from '@/shared/theme/theme-context-value';
import { DropdownMenuLabel, DropdownMenuRadioGroup, DropdownMenuRadioItem } from '@/shared/ui/DropdownMenu';

const appearanceIcons: Record<ThemePreference, typeof Sun> = {
  auto: Monitor,
  dark: Moon,
  light: Sun,
};

const appearancePreferences: ThemePreference[] = ['auto', 'light', 'dark'];

function isThemePreference(value: unknown): value is ThemePreference {
  return value === 'auto' || value === 'dark' || value === 'light';
}

/** The appearance choices offered inside the workspace account menu. */
export function AppearanceRadioGroup({
  onValueChange,
  value,
}: {
  onValueChange: (preference: ThemePreference) => void;
  value: ThemePreference;
}) {
  const { t } = useI18n();

  return (
    <DropdownMenuRadioGroup
      value={value}
      onValueChange={(nextPreference) => {
        if (isThemePreference(nextPreference)) onValueChange(nextPreference);
      }}
    >
      <DropdownMenuLabel>{t('settings.appearance')}</DropdownMenuLabel>
      {appearancePreferences.map((preference) => {
        const Icon = appearanceIcons[preference];
        return (
          <DropdownMenuRadioItem closeOnClick key={preference} value={preference}>
            <span className="inline-flex items-center gap-2">
              <Icon className="size-4 text-subtle-foreground" />
              {t(`settings.${preference}`)}
            </span>
          </DropdownMenuRadioItem>
        );
      })}
    </DropdownMenuRadioGroup>
  );
}
