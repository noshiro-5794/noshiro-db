import { type ChangeEvent, type FormEvent, useMemo, useState } from 'react';
import { Palette, Upload } from 'lucide-react';
import { profileApi } from '@/features/auth/api';
import type { AuthState } from '@/features/auth/auth-context-value';
import { useI18n } from '@/features/i18n/use-i18n';
import type { CurrentUserProfile } from '@/lib/api/types';
import { Button } from '@/shared/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/Card';
import { Input } from '@/shared/ui/Input';

type ProfileOverviewProps = {
  auth: AuthState;
  profile: CurrentUserProfile | null;
};

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Request failed';
}

export function ProfileOverview({ auth, profile }: ProfileOverviewProps) {
  const { t } = useI18n();
  const [nickname, setNickname] = useState(profile?.nickname ?? '');
  const [bio, setBio] = useState(profile?.bio ?? '');
  const [themeColor, setThemeColor] = useState(profile?.theme_color ?? '#7F6FB0');
  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [noticeMessage, setNoticeMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const avatarUrl = profile?.avatar || '/assets/placeholders/avatar.png';
  const colorInputValue = /^#[0-9a-fA-F]{6}$/.test(themeColor) ? themeColor : '#7F6FB0';
  const roleLabel = profile?.is_superuser || profile?.is_staff ? t('auth.admin') : t('auth.user');
  const profileMeta = useMemo(
    () => [
      { label: t('me.role'), value: roleLabel },
      { label: t('me.email'), value: profile?.email ?? '-' },
      { label: t('me.userId'), value: profile?.user_id ? String(profile.user_id) : '-' },
    ],
    [profile?.email, profile?.user_id, roleLabel, t],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setNoticeMessage('');
    setErrorMessage('');

    try {
      await profileApi.updateMe({
        nickname: nickname.trim(),
        bio,
        theme_color: themeColor,
      });
      await auth.refreshSession();
      setNoticeMessage(t('me.saved'));
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleAvatarChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setIsUploading(true);
    setNoticeMessage('');
    setErrorMessage('');
    try {
      await profileApi.uploadAvatar(file);
      await auth.refreshSession();
      setNoticeMessage(t('me.avatarSaved'));
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsUploading(false);
      event.target.value = '';
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
      <aside className="grid content-start gap-4">
        <Card>
          <CardContent className="grid justify-items-center gap-4 p-5 text-center">
            <img className="size-24 rounded-2xl bg-neutral-100 object-cover ring-1 ring-neutral-200 dark:bg-neutral-900 dark:ring-neutral-800" src={avatarUrl} alt="" />
            <div>
              <h2 className="text-xl font-semibold tracking-tight text-neutral-950 dark:text-white">{profile?.nickname}</h2>
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{profile?.email}</p>
            </div>
            <label className="inline-flex cursor-pointer">
              <input accept="image/jpeg,image/png,image/webp" className="sr-only" type="file" onChange={handleAvatarChange} />
              <span className="inline-flex h-10 items-center gap-2 rounded-full border border-neutral-200 bg-white px-4 text-sm font-semibold text-neutral-800 shadow-sm transition hover:border-neutral-300 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-100">
                <Upload className="size-4" />
                {isUploading ? t('me.uploading') : t('me.uploadAvatar')}
              </span>
            </label>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('me.account')}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            {profileMeta.map((item) => (
              <div className="flex items-center justify-between gap-4 text-sm" key={item.label}>
                <span className="text-neutral-500 dark:text-neutral-400">{item.label}</span>
                <span className="truncate font-medium text-neutral-950 dark:text-white">{item.value}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </aside>

      <section className="grid content-start gap-4">
        <Card>
          <CardHeader>
            <CardTitle>{t('me.profileSettings')}</CardTitle>
            <CardDescription>{t('me.profileSettingsBody')}</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="grid gap-4" onSubmit={handleSubmit}>
              <label className="grid gap-2">
                <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">{t('auth.nickname')}</span>
                <Input required maxLength={32} value={nickname} onChange={(event) => setNickname(event.target.value)} />
              </label>

              <label className="grid gap-2">
                <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">{t('me.bio')}</span>
                <textarea
                  className="min-h-32 w-full resize-y rounded-xl border-0 bg-white px-4 py-3 text-sm shadow-sm outline-none ring-1 ring-neutral-200 transition placeholder:text-neutral-400 focus:ring-4 focus:ring-neutral-200 dark:bg-neutral-950 dark:ring-neutral-800 dark:focus:ring-neutral-800"
                  maxLength={500}
                  value={bio}
                  onChange={(event) => setBio(event.target.value)}
                />
              </label>

              <label className="grid gap-2">
                <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">{t('me.themeColor')}</span>
                <span className="grid grid-cols-[44px_minmax(0,1fr)] gap-3">
                  <input
                    className="h-11 w-11 cursor-pointer rounded-xl border-0 bg-transparent p-0"
                    type="color"
                    value={colorInputValue}
                    onChange={(event) => setThemeColor(event.target.value)}
                  />
                  <Input pattern="^#[0-9a-fA-F]{6}$" value={themeColor} onChange={(event) => setThemeColor(event.target.value)} />
                </span>
              </label>

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

              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="inline-flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
                  <Palette className="size-4" />
                  {t('me.themeHint')}
                </span>
                <Button disabled={isSaving || auth.loading} type="submit">
                  {isSaving ? t('me.saving') : t('me.saveProfile')}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardContent className="p-5">
              <strong className="text-2xl text-neutral-950 dark:text-white">0</strong>
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{t('me.watching')}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <strong className="text-2xl text-neutral-950 dark:text-white">0</strong>
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{t('me.completed')}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <strong className="text-2xl text-neutral-950 dark:text-white">0</strong>
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{t('me.reviews')}</p>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
