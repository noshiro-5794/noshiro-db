import { type ChangeEvent, type FormEvent, type PointerEvent, useEffect, useState } from 'react';
import { Link, Navigate, useNavigate } from '@/shared/routing/navigation';
import { Crop, KeyRound, LogOut, Palette, Upload } from 'lucide-react';
import { profileApi } from '@/entities/session';
import { useAuth } from '@/entities/session';
import { useI18n } from '@/shared/i18n';
import { useTheme } from '@/shared/theme/use-theme';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/Card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { EmptyState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';
import { PublicFooter } from '@/widgets/public-footer';

const defaultAccentColor = '#7F6FB0';
const avatarPlaceholder = '/assets/placeholders/avatar.png';
type LanguagePreference = 'auto' | 'en-US' | 'zh-CN' | 'ja-JP';
type AppearancePreference = 'auto' | 'light' | 'dark';

type AvatarDraft = {
  file: File;
  url: string;
  width: number;
  height: number;
};

type AvatarOffset = {
  x: number;
  y: number;
};

type AvatarDragState = {
  pointerId: number;
  startX: number;
  startY: number;
  offset: AvatarOffset;
  previewWidth: number;
  previewHeight: number;
};

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = src;
  });
}

function getAvatarCropGeometry(width: number, height: number, zoom: number, offset: AvatarOffset) {
  const sourceSize = Math.min(width, height) / zoom;
  const maxSourceX = width - sourceSize;
  const maxSourceY = height - sourceSize;
  const sourceX = clamp(maxSourceX / 2 + offset.x * (maxSourceX / 2), 0, maxSourceX);
  const sourceY = clamp(maxSourceY / 2 + offset.y * (maxSourceY / 2), 0, maxSourceY);
  return { sourceSize, sourceX, sourceY };
}

async function createSquareAvatarFile(file: File, sourceUrl: string, zoom: number, offset: AvatarOffset) {
  const image = await loadImage(sourceUrl);
  const { sourceSize, sourceX, sourceY } = getAvatarCropGeometry(image.naturalWidth, image.naturalHeight, zoom, offset);
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 512;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('Canvas is unavailable.');
  context.imageSmoothingQuality = 'high';
  context.drawImage(image, sourceX, sourceY, sourceSize, sourceSize, 0, 0, canvas.width, canvas.height);

  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (result) => (result ? resolve(result) : reject(new Error('Unable to crop image.'))),
      'image/webp',
      0.92,
    );
  });
  return new File([blob], `${file.name.replace(/\.[^.]+$/, '') || 'avatar'}-cropped.webp`, { type: 'image/webp' });
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
  const [avatarDraft, setAvatarDraft] = useState<AvatarDraft | null>(null);
  const [avatarZoom, setAvatarZoom] = useState(1);
  const [avatarOffset, setAvatarOffset] = useState<AvatarOffset>({ x: 0, y: 0 });
  const [avatarDrag, setAvatarDrag] = useState<AvatarDragState | null>(null);
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
    void navigate(routes.home, { replace: true });
  }

  useEffect(() => {
    setNickname(profile?.nickname ?? '');
    setBio(profile?.bio ?? '');
    setLanguage(profile?.language ?? 'auto');
    setAppearance(profile?.appearance ?? 'auto');
    setThemeColor(profile?.theme_color || defaultAccentColor);
  }, [profile]);

  useEffect(
    () => () => {
      if (avatarDraft) URL.revokeObjectURL(avatarDraft.url);
    },
    [avatarDraft],
  );

  if (auth.status === 'checking') {
    return (
      <Page title={i18n.t('settings.title')} eyebrow={i18n.t('nav.groupMore')}>
        <LoadingState title={i18n.t('auth.checking')} />
      </Page>
    );
  }

  if (auth.role === 'guest') {
    return <Navigate replace to={routes.login} />;
  }

  if (!profile) {
    return (
      <Page title={i18n.t('settings.title')} eyebrow={i18n.t('nav.groupMore')}>
        <EmptyState
          title={i18n.t('settings.profileUnavailableTitle')}
          description={i18n.t('settings.profileUnavailableBody')}
        />
      </Page>
    );
  }

  async function handleAvatarChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setNoticeMessage('');
    setErrorMessage('');
    setAvatarZoom(1);
    setAvatarOffset({ x: 0, y: 0 });
    setAvatarDrag(null);
    const url = URL.createObjectURL(file);
    try {
      const image = await loadImage(url);
      setAvatarDraft((currentDraft) => {
        if (currentDraft) URL.revokeObjectURL(currentDraft.url);
        return { file, url, width: image.naturalWidth, height: image.naturalHeight };
      });
    } catch (error) {
      URL.revokeObjectURL(url);
      setErrorMessage(getErrorMessage(error, i18n.t('common.requestFailed')));
    }
  }

  function closeAvatarDraft() {
    setAvatarDraft((currentDraft) => {
      if (currentDraft) URL.revokeObjectURL(currentDraft.url);
      return null;
    });
    setAvatarZoom(1);
    setAvatarOffset({ x: 0, y: 0 });
    setAvatarDrag(null);
  }

  async function uploadAvatarFile(file: File) {
    setIsUploading(true);
    setNoticeMessage('');
    setErrorMessage('');
    try {
      await profileApi.uploadAvatar(file);
      await auth.refreshSession();
      setNoticeMessage(i18n.t('settings.avatarUpdated'));
      closeAvatarDraft();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, i18n.t('common.requestFailed')));
    } finally {
      setIsUploading(false);
    }
  }

  async function uploadCroppedAvatar() {
    if (!avatarDraft) return;
    setIsUploading(true);
    setNoticeMessage('');
    setErrorMessage('');
    try {
      const croppedFile = await createSquareAvatarFile(avatarDraft.file, avatarDraft.url, avatarZoom, avatarOffset);
      await profileApi.uploadAvatar(croppedFile);
      await auth.refreshSession();
      setNoticeMessage(i18n.t('settings.avatarUpdated'));
      closeAvatarDraft();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, i18n.t('common.requestFailed')));
    } finally {
      setIsUploading(false);
    }
  }

  function updateAvatarOffset(nextOffset: AvatarOffset) {
    setAvatarOffset({
      x: clamp(nextOffset.x, -1, 1),
      y: clamp(nextOffset.y, -1, 1),
    });
  }

  function handleAvatarPointerDown(event: PointerEvent<HTMLDivElement>) {
    const previewRect = event.currentTarget.parentElement?.getBoundingClientRect();
    event.currentTarget.setPointerCapture(event.pointerId);
    setAvatarDrag({
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      offset: avatarOffset,
      previewWidth: previewRect?.width || 1,
      previewHeight: previewRect?.height || 1,
    });
  }

  function handleAvatarPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!avatarDraft || !avatarDrag || avatarDrag.pointerId !== event.pointerId) return;
    const { sourceSize } = getAvatarCropGeometry(avatarDraft.width, avatarDraft.height, avatarZoom, avatarDrag.offset);
    const maxSourceX = avatarDraft.width - sourceSize;
    const maxSourceY = avatarDraft.height - sourceSize;
    const deltaSourceX = (event.clientX - avatarDrag.startX) * (avatarDraft.width / avatarDrag.previewWidth);
    const deltaSourceY = (event.clientY - avatarDrag.startY) * (avatarDraft.height / avatarDrag.previewHeight);
    updateAvatarOffset({
      x: maxSourceX > 0 ? avatarDrag.offset.x + deltaSourceX / (maxSourceX / 2) : 0,
      y: maxSourceY > 0 ? avatarDrag.offset.y + deltaSourceY / (maxSourceY / 2) : 0,
    });
  }

  function handleAvatarPointerUp(event: PointerEvent<HTMLDivElement>) {
    if (avatarDrag?.pointerId === event.pointerId) {
      setAvatarDrag(null);
    }
  }

  const avatarCropGeometry = avatarDraft
    ? getAvatarCropGeometry(avatarDraft.width, avatarDraft.height, avatarZoom, avatarOffset)
    : null;

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
        i18n.setLocale(language);
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
    <Page title={i18n.t('settings.title')} eyebrow={i18n.t('nav.groupMore')}>
      <div className="grid gap-8 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="grid content-start gap-6">
          <section className="lg:sticky lg:top-6">
            <div className="flex items-center gap-4 lg:block">
              <img
                className="size-24 rounded-full bg-neutral-100 object-cover ring-1 ring-neutral-200 dark:bg-neutral-900 dark:ring-neutral-800 lg:size-28"
                src={profile.avatar || avatarPlaceholder}
                alt=""
              />
              <div className="min-w-0 lg:mt-4">
                <h2 className="truncate text-xl font-semibold tracking-tight text-neutral-950 dark:text-white">
                  {profile.nickname}
                </h2>
                <p className="mt-1 truncate text-sm text-neutral-500 dark:text-neutral-400">{profile.email}</p>
              </div>
            </div>

            <div className="mt-5 grid gap-2">
              <label className="inline-flex cursor-pointer">
                <input
                  accept="image/jpeg,image/png,image/webp"
                  className="sr-only"
                  type="file"
                  onChange={(event) => void handleAvatarChange(event)}
                />
                <span className="button button-secondary w-full">
                  <Upload className="size-4" />
                  {isUploading ? i18n.t('me.uploading') : i18n.t('settings.uploadAvatar')}
                </span>
              </label>
            </div>

            <div className="mt-6 border-t border-neutral-200 pt-5 dark:border-neutral-800">
              <h2 className="text-sm font-semibold text-neutral-950 dark:text-white">{i18n.t('settings.security')}</h2>
            </div>
            <div className="mt-4 grid gap-2">
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
            </div>
          </section>
        </aside>

        <main className="grid content-start gap-5">
          <Card className="shadow-none">
            <CardHeader>
              <CardTitle>{i18n.t('settings.profile')}</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-4" onSubmit={(event) => void handleProfileSubmit(event)}>
                <label className="grid gap-2 text-sm font-medium text-[var(--color-text)]">
                  {i18n.t('auth.nickname')}
                  <Input
                    required
                    maxLength={32}
                    value={nickname}
                    onChange={(event) => setNickname(event.target.value)}
                  />
                </label>
                <label className="grid gap-2 text-sm font-medium text-[var(--color-text)]">
                  {i18n.t('me.bio')}
                  <textarea
                    className="min-h-32 w-full resize-y rounded-xl border-0 bg-[var(--color-surface)] px-4 py-3 text-sm text-[var(--color-text)] shadow-sm outline-none ring-1 ring-[var(--color-border)] transition placeholder:text-neutral-400 focus:ring-4 focus:ring-[var(--color-focus-ring)]"
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

          <Card className="shadow-none">
            <CardHeader>
              <CardTitle>{i18n.t('settings.preferences')}</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-4" onSubmit={(event) => void handleSettingsSubmit(event)}>
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
                <label className="grid gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                  {i18n.t('settings.accentColor')}
                  <span className="grid grid-cols-[44px_minmax(0,1fr)] gap-3">
                    <input
                      className="h-11 w-11 cursor-pointer rounded-xl border-0 bg-transparent p-0"
                      type="color"
                      value={/^#[0-9a-fA-F]{6}$/.test(themeColor) ? themeColor : defaultAccentColor}
                      onChange={(event) => setThemeColor(event.target.value)}
                    />
                    <Input
                      pattern="^#[0-9a-fA-F]{6}$"
                      value={themeColor}
                      onChange={(event) => setThemeColor(event.target.value)}
                    />
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
          <PublicFooter variant="compact" />
        </main>
      </div>

      <Dialog open={Boolean(avatarDraft)} onOpenChange={(open) => !open && closeAvatarDraft()}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>{i18n.t('settings.avatarDialogTitle')}</DialogTitle>
            <DialogDescription>{i18n.t('settings.avatarDialogDescription')}</DialogDescription>
          </DialogHeader>
          {avatarDraft ? (
            <div className="grid gap-5">
              <div className="grid gap-4 sm:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
                <div
                  className="relative mx-auto w-full max-w-80 overflow-hidden rounded-2xl bg-neutral-100 ring-1 ring-neutral-200 dark:bg-neutral-900 dark:ring-neutral-800"
                  style={{ aspectRatio: `${avatarDraft.width} / ${avatarDraft.height}` }}
                >
                  <img
                    alt=""
                    className="absolute inset-0 size-full select-none object-contain"
                    draggable={false}
                    src={avatarDraft.url}
                  />
                  {avatarCropGeometry ? (
                    <div
                      className={`absolute touch-none rounded-xl border-2 border-white shadow-[0_0_0_999px_rgb(0_0_0/0.28)] ring-1 ring-black/10 dark:border-neutral-950 dark:ring-white/20 ${avatarDrag ? 'cursor-grabbing' : 'cursor-grab'}`}
                      role="application"
                      aria-label={i18n.t('settings.avatarCropFrame')}
                      style={{
                        left: `${(avatarCropGeometry.sourceX / avatarDraft.width) * 100}%`,
                        top: `${(avatarCropGeometry.sourceY / avatarDraft.height) * 100}%`,
                        width: `${(avatarCropGeometry.sourceSize / avatarDraft.width) * 100}%`,
                        height: `${(avatarCropGeometry.sourceSize / avatarDraft.height) * 100}%`,
                      }}
                      onPointerCancel={handleAvatarPointerUp}
                      onPointerDown={handleAvatarPointerDown}
                      onPointerMove={handleAvatarPointerMove}
                      onPointerUp={handleAvatarPointerUp}
                    >
                      <span className="pointer-events-none absolute inset-3 rounded-lg border border-white/60 dark:border-white/20" />
                    </div>
                  ) : null}
                </div>
                <div className="grid content-center gap-4">
                  <div className="grid gap-2">
                    <div className="flex items-center justify-between gap-3 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                      <span>{i18n.t('settings.avatarZoom')}</span>
                      <span className="tabular-nums text-neutral-400">{Math.round(avatarZoom * 100)}%</span>
                    </div>
                    <input
                      className="w-full accent-[var(--color-accent)]"
                      max="2"
                      min="1"
                      step="0.01"
                      type="range"
                      value={avatarZoom}
                      onChange={(event) => setAvatarZoom(Number(event.target.value))}
                    />
                  </div>
                  <div className="grid gap-2">
                    <div className="flex items-center justify-between gap-3 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                      <span>{i18n.t('settings.avatarPositionX')}</span>
                      <span className="tabular-nums text-neutral-400">{Math.round(avatarOffset.x * 100)}</span>
                    </div>
                    <input
                      className="w-full accent-[var(--color-accent)]"
                      max="1"
                      min="-1"
                      step="0.01"
                      type="range"
                      value={avatarOffset.x}
                      onChange={(event) => updateAvatarOffset({ ...avatarOffset, x: Number(event.target.value) })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <div className="flex items-center justify-between gap-3 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                      <span>{i18n.t('settings.avatarPositionY')}</span>
                      <span className="tabular-nums text-neutral-400">{Math.round(avatarOffset.y * 100)}</span>
                    </div>
                    <input
                      className="w-full accent-[var(--color-accent)]"
                      max="1"
                      min="-1"
                      step="0.01"
                      type="range"
                      value={avatarOffset.y}
                      onChange={(event) => updateAvatarOffset({ ...avatarOffset, y: Number(event.target.value) })}
                    />
                  </div>
                  <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm leading-6 text-neutral-500 dark:border-neutral-800 dark:bg-neutral-900/60 dark:text-neutral-400">
                    {i18n.t('settings.avatarCropHint')}
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                <Button disabled={isUploading} type="button" variant="ghost" onClick={closeAvatarDraft}>
                  {i18n.t('common.cancel')}
                </Button>
                <Button
                  disabled={isUploading}
                  type="button"
                  variant="secondary"
                  onClick={() => void uploadAvatarFile(avatarDraft.file)}
                >
                  <Upload className="size-4" />
                  {i18n.t('settings.uploadOriginal')}
                </Button>
                <Button disabled={isUploading} type="button" onClick={() => void uploadCroppedAvatar()}>
                  <Crop className="size-4" />
                  {isUploading ? i18n.t('me.uploading') : i18n.t('settings.uploadCropped')}
                </Button>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </Page>
  );
}
