import { type SyntheticEvent, useId, useState } from 'react';
import { profileApi, type SessionProfilePatch } from '@/entities/session';
import type { CurrentUserProfile } from '@/shared/api';
import { type MessageKey, useI18n } from '@/shared/i18n';
import { getErrorMessage } from '@/shared/lib/error';
import { Button } from '@/shared/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/Card';
import { Field, FieldLabel } from '@/shared/ui/Field';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
import { Textarea } from '@/shared/ui/Textarea';

type SettingsFormProps = {
  profile: CurrentUserProfile;
  patchProfile: (patch: SessionProfilePatch) => void;
  onError: (message: string) => void;
  onNotice: (messageKey: MessageKey) => void;
};

type LanguagePreference = NonNullable<CurrentUserProfile['language']>;
type AppearancePreference = NonNullable<CurrentUserProfile['appearance']>;

export function ProfileSettingsForm({ profile, patchProfile, onError, onNotice }: SettingsFormProps) {
  const { t } = useI18n();
  const [nickname, setNickname] = useState(profile.nickname);
  const [bio, setBio] = useState(profile.bio ?? '');
  const [isSaving, setIsSaving] = useState(false);
  const nicknameId = useId();
  const bioId = useId();

  async function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    const nextNickname = nickname.trim();
    if (isSaving || !nextNickname) return;
    setIsSaving(true);
    try {
      const nextProfile = await profileApi.updateMe({ nickname: nextNickname, bio });
      patchProfile({ nickname: nextProfile.nickname, bio: nextProfile.bio ?? '' });
      onNotice('settings.profileUpdated');
    } catch (error) {
      onError(getErrorMessage(error, t('common.requestFailed')));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Card className="shadow-none">
      <CardHeader>
        <CardTitle>{t('settings.profile')}</CardTitle>
      </CardHeader>
      <CardContent>
        <form aria-busy={isSaving} className="grid gap-4" onSubmit={(event) => void submit(event)}>
          <Field>
            <FieldLabel htmlFor={nicknameId}>{t('auth.nickname')}</FieldLabel>
            <Input
              required
              autoComplete="nickname"
              id={nicknameId}
              maxLength={32}
              minLength={1}
              name="nickname"
              value={nickname}
              onChange={(event) => {
                setNickname(event.target.value);
              }}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor={bioId}>{t('me.bio')}</FieldLabel>
            <Textarea
              className="min-h-32"
              id={bioId}
              maxLength={500}
              name="bio"
              value={bio}
              onChange={(event) => {
                setBio(event.target.value);
              }}
            />
          </Field>
          <Button className="justify-self-end" disabled={isSaving} type="submit">
            {isSaving ? t('common.saving') : t('me.saveProfile')}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export function PreferenceSettingsForm({ profile, patchProfile, onError, onNotice }: SettingsFormProps) {
  const i18n = useI18n();
  const [language, setLanguage] = useState<LanguagePreference>(profile.language ?? 'auto');
  const [appearance, setAppearance] = useState<AppearancePreference>(profile.appearance ?? 'auto');
  const [isSaving, setIsSaving] = useState(false);
  const languageOptions: Array<{ label: string; value: LanguagePreference }> = [
    { label: i18n.t('settings.auto'), value: 'auto' },
    { label: 'English', value: 'en-US' },
    { label: '简体中文', value: 'zh-CN' },
    { label: '日本語', value: 'ja-JP' },
  ];
  const appearanceOptions: Array<{ label: string; value: AppearancePreference }> = [
    { label: i18n.t('settings.auto'), value: 'auto' },
    { label: i18n.t('settings.light'), value: 'light' },
    { label: i18n.t('settings.dark'), value: 'dark' },
  ];

  async function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (isSaving) return;
    setIsSaving(true);
    try {
      const nextProfile = await profileApi.updateSettings({ language, appearance });
      patchProfile({
        language: nextProfile.language ?? language,
        appearance: nextProfile.appearance ?? appearance,
      });
      onNotice('settings.settingsUpdated');
    } catch (error) {
      onError(getErrorMessage(error, i18n.t('common.requestFailed')));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Card className="shadow-none">
      <CardHeader>
        <CardTitle>{i18n.t('settings.preferences')}</CardTitle>
      </CardHeader>
      <CardContent>
        <form aria-busy={isSaving} className="grid gap-4" onSubmit={(event) => void submit(event)}>
          <div className="grid gap-3 md:grid-cols-2">
            <FilterMenu
              label={i18n.t('settings.language')}
              options={languageOptions}
              value={language}
              onChange={setLanguage}
            />
            <FilterMenu
              label={i18n.t('settings.appearance')}
              options={appearanceOptions}
              value={appearance}
              onChange={setAppearance}
            />
          </div>
          <div className="flex justify-end">
            <Button disabled={isSaving} type="submit">
              {isSaving ? i18n.t('common.saving') : i18n.t('settings.savePreferences')}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
