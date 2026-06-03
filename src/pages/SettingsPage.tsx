import { type ChangeEvent, type FormEvent, useEffect, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { KeyRound, LogOut, Palette, Upload } from 'lucide-react';
import { profileApi } from '@/features/auth/api';
import { useAuth } from '@/features/auth/use-auth';
import { useI18n } from '@/features/i18n/use-i18n';
import type { Locale } from '@/features/i18n/messages';
import { useTheme } from '@/features/theme/use-theme';
import { routes } from '@/routes/paths';
import { Button } from '@/shared/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/Card';
import { EmptyState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';

const defaultAccentColor = '#7F6FB0';
const avatarPlaceholder = '/assets/placeholders/avatar.png';
type LanguagePreference = 'auto' | 'en-US' | 'zh-CN' | 'ja-JP';
type AppearancePreference = 'auto' | 'light' | 'dark';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function SettingsPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const i18n = useI18n();
  const theme = useTheme();
  const profile = auth.profile;
  const [nickname, setNickname] = useState(profile?.nickname ?? '');
  const [bio, setBio] = useState(profile?.bio ?? '');
  const [language, setLanguage] = useState<LanguagePreference>(profile?.language ?? 'auto');
  const [appearance, setAppearance] = useState<AppearancePreference>(profile?.appearance ?? 'auto');
  const [themeColor, setThemeColor] = useState(profile?.theme_color || defaultAccentColor);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [noticeMessage, setNoticeMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
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

  async function handleSignOut() {
    await auth.logout();
    navigate(routes.home, { replace: true });
  }

  useEffect(() => {
    setNickname(profile?.nickname ?? '');
    setBio(profile?.bio ?? '');
    setLanguage(profile?.language ?? 'auto');
    setAppearance(profile?.appearance ?? 'auto');
    setThemeColor(profile?.theme_color || defaultAccentColor);
  }, [profile]);

  if (auth.status === 'checking') {
    return (
      <Page title={i18n.t('settings.title')} description={i18n.t('settings.loadingDescription')}>
        <LoadingState title={i18n.t('auth.checking')} />
      </Page>
    );
  }

  if (auth.role === 'guest') {
    return <Navigate replace to={routes.login} />;
  }

  if (!profile) {
    return (
      <Page title={i18n.t('settings.title')}>
        <EmptyState title={i18n.t('settings.profileUnavailableTitle')} description={i18n.t('settings.profileUnavailableBody')} />
      </Page>
    );
  }

  async function handleAvatarChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setNoticeMessage('');
    setErrorMessage('');
    try {
      await profileApi.uploadAvatar(file);
      await auth.refreshSession();
      setNoticeMessage(i18n.t('settings.avatarUpdated'));
    } catch (error) {
      setErrorMessage(getErrorMessage(error, i18n.t('common.requestFailed')));
    } finally {
      setIsUploading(false);
      event.target.value = '';
    }
  }

  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSavingProfile(true);
    setNoticeMessage('');
    setErrorMessage('');
    try {
      await profileApi.updateMe({
        nickname: nickname.trim(),
        bio,
        theme_color: themeColor,
      });
      await auth.refreshSession();
      setNoticeMessage(i18n.t('settings.profileUpdated'));
    } catch (error) {
      setErrorMessage(getErrorMessage(error, i18n.t('common.requestFailed')));
    } finally {
      setIsSavingProfile(false);
    }
  }

  async function handleSettingsSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSavingSettings(true);
    setNoticeMessage('');
    setErrorMessage('');
    try {
      await profileApi.updateSettings({
        language,
        appearance,
        theme_color: themeColor || defaultAccentColor,
      });
      theme.setMode(appearance);
      theme.setAccentColor(themeColor || defaultAccentColor);
      if (language !== 'auto') {
        i18n.setLocale(language as Locale);
      }
      await auth.refreshSession();
      setNoticeMessage(i18n.t('settings.settingsUpdated'));
    } catch (error) {
      setErrorMessage(getErrorMessage(error, i18n.t('common.requestFailed')));
    } finally {
      setIsSavingSettings(false);
    }
  }

  return (
    <Page title={i18n.t('settings.title')} eyebrow={i18n.t('settings.title')} description={i18n.t('settings.description')}>
      <div className="grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="grid content-start gap-4">
          <Card>
            <CardContent className="grid justify-items-center gap-4 p-5 text-center">
              <img className="size-24 rounded-2xl bg-neutral-100 object-cover ring-1 ring-neutral-200 dark:bg-neutral-900 dark:ring-neutral-800" src={profile.avatar || avatarPlaceholder} alt="" />
              <div>
                <h2 className="font-semibold text-neutral-950 dark:text-white">{profile.nickname}</h2>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{profile.email}</p>
              </div>
              <label className="inline-flex cursor-pointer">
                <input accept="image/jpeg,image/png,image/webp" className="sr-only" type="file" onChange={handleAvatarChange} />
                <span className="button button-secondary">
                  <Upload className="size-4" />
                  {isUploading ? i18n.t('me.uploading') : i18n.t('settings.uploadAvatar')}
                </span>
              </label>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{i18n.t('settings.security')}</CardTitle>
              <CardDescription>{i18n.t('settings.securityDescription')}</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3">
              <Button asChild variant="secondary">
                <Link to={routes.resetPassword}>
                  <KeyRound className="size-4" />
                  {i18n.t('settings.changePassword')}
                </Link>
              </Button>
              <Button type="button" variant="ghost" onClick={() => void handleSignOut()}>
                <LogOut className="size-4" />
                {i18n.t('settings.signOut')}
              </Button>
            </CardContent>
          </Card>
        </aside>

        <main className="grid content-start gap-5">
          <Card>
            <CardHeader>
              <CardTitle>{i18n.t('settings.profile')}</CardTitle>
              <CardDescription>{i18n.t('settings.profileDescription')}</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="grid gap-4" onSubmit={handleProfileSubmit}>
                <label className="grid gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                  {i18n.t('auth.nickname')}
                  <Input required maxLength={32} value={nickname} onChange={(event) => setNickname(event.target.value)} />
                </label>
                <label className="grid gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                  {i18n.t('me.bio')}
                  <textarea
                    className="min-h-32 w-full resize-y rounded-xl border-0 bg-white px-4 py-3 text-sm shadow-sm outline-none ring-1 ring-neutral-200 transition placeholder:text-neutral-400 focus:ring-4 focus:ring-neutral-200 dark:bg-neutral-950 dark:ring-neutral-800 dark:focus:ring-neutral-800"
                    maxLength={500}
                    value={bio}
                    onChange={(event) => setBio(event.target.value)}
                  />
                </label>
                <Button className="justify-self-end" disabled={isSavingProfile || auth.loading} type="submit">
                  {isSavingProfile ? i18n.t('common.saving') : i18n.t('me.saveProfile')}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{i18n.t('settings.preferences')}</CardTitle>
              <CardDescription>{i18n.t('settings.preferencesDescription')}</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="grid gap-4" onSubmit={handleSettingsSubmit}>
                <div className="grid gap-3 md:grid-cols-2">
                  <FilterMenu label={i18n.t('settings.language')} options={languageOptions} value={language} onChange={setLanguage} />
                  <FilterMenu label={i18n.t('settings.appearance')} options={appearanceOptions} value={appearance} onChange={setAppearance} />
                </div>
                <label className="grid gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                  {i18n.t('settings.accentColor')}
                  <span className="grid grid-cols-[44px_minmax(0,1fr)] gap-3">
                    <input
                      className="h-11 w-11 cursor-pointer rounded-xl border-0 bg-transparent p-0"
                      type="color"
                      value={/^#[0-9a-fA-F]{6}$/.test(themeColor) ? themeColor : defaultAccentColor}
                      onChange={(event) => setThemeColor(event.target.value)}
                    />
                    <Input pattern="^#[0-9a-fA-F]{6}$" value={themeColor} onChange={(event) => setThemeColor(event.target.value)} />
                  </span>
                </label>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="inline-flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
                    <Palette className="size-4" />
                    {i18n.t('settings.defaultAccent')} {defaultAccentColor}.
                  </span>
                  <Button disabled={isSavingSettings || auth.loading} type="submit">
                    {isSavingSettings ? i18n.t('common.saving') : i18n.t('settings.savePreferences')}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {noticeMessage ? <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">{noticeMessage}</p> : null}
          {errorMessage ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-300">{errorMessage}</p> : null}
        </main>
      </div>
    </Page>
  );
}
