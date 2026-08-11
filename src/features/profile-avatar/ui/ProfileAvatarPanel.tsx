import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { type ChangeEvent, useEffect, useRef, useState } from 'react';
import { Link } from '@tanstack/react-router';
import { KeyRound, LogOut, Upload } from 'lucide-react';
import { profileApi, type SessionProfilePatch } from '@/entities/session';
import type { CurrentUserProfile } from '@/shared/api';
import { type MessageKey, useI18n } from '@/shared/i18n';
import { getErrorMessage } from '@/shared/lib/error';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import { type AvatarDraft, loadAvatarImage } from '../model/avatar-crop';
import {
  AvatarImageError,
  validateAvatarDimensions,
  validateAvatarFile,
  type AvatarImageErrorCode,
} from '../model/avatar-image';
import { AvatarCropDialog } from './AvatarCropDialog';

const avatarPlaceholder = placeholderImagePaths.avatar;

const avatarErrorMessageKeys: Record<AvatarImageErrorCode, Parameters<ReturnType<typeof useI18n>['t']>[0]> = {
  'invalid-content': 'settings.avatarInvalidContent',
  'invalid-dimensions': 'settings.avatarInvalidDimensions',
  'too-large': 'settings.avatarTooLarge',
  'unsupported-type': 'settings.avatarUnsupportedType',
};

type ProfileAvatarPanelProps = {
  profile: CurrentUserProfile;
  patchProfile: (patch: SessionProfilePatch) => void;
  sessionBusy: boolean;
  onError: (message: string) => void;
  onNotice: (messageKey: MessageKey) => void;
  onSignOut: () => Promise<void>;
};

export function ProfileAvatarPanel({
  profile,
  patchProfile,
  sessionBusy,
  onError,
  onNotice,
  onSignOut,
}: ProfileAvatarPanelProps) {
  const { t } = useI18n();
  const [isUploading, setIsUploading] = useState(false);
  const [avatarDraft, setAvatarDraft] = useState<AvatarDraft | null>(null);
  const avatarDraftRef = useRef<AvatarDraft | null>(null);
  const selectionIdRef = useRef(0);

  function replaceAvatarDraft(nextDraft: AvatarDraft | null) {
    const previousDraft = avatarDraftRef.current;
    if (previousDraft && previousDraft.url !== nextDraft?.url) URL.revokeObjectURL(previousDraft.url);
    avatarDraftRef.current = nextDraft;
    setAvatarDraft(nextDraft);
  }

  useEffect(
    () => () => {
      selectionIdRef.current += 1;
      if (avatarDraftRef.current) URL.revokeObjectURL(avatarDraftRef.current.url);
      avatarDraftRef.current = null;
    },
    [],
  );

  async function selectAvatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || isUploading) return;
    const selectionId = selectionIdRef.current + 1;
    selectionIdRef.current = selectionId;
    let url: string | null = null;
    try {
      await validateAvatarFile(file);
      if (selectionIdRef.current !== selectionId) return;

      url = URL.createObjectURL(file);
      const image = await loadAvatarImage(url);
      validateAvatarDimensions(image.naturalWidth, image.naturalHeight);
      if (selectionIdRef.current !== selectionId) {
        URL.revokeObjectURL(url);
        return;
      }

      replaceAvatarDraft({ file, url, width: image.naturalWidth, height: image.naturalHeight });
    } catch (error) {
      if (url) URL.revokeObjectURL(url);
      if (selectionIdRef.current === selectionId) {
        onError(
          error instanceof AvatarImageError
            ? t(avatarErrorMessageKeys[error.code])
            : getErrorMessage(error, t('common.requestFailed')),
        );
      }
    }
  }

  async function uploadAvatar(file: File) {
    if (isUploading) return;
    setIsUploading(true);
    try {
      const { avatar } = await profileApi.uploadAvatar(file);
      patchProfile({ avatar });
      onNotice('settings.avatarUpdated');
      replaceAvatarDraft(null);
    } catch (error) {
      onError(getErrorMessage(error, t('common.requestFailed')));
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <aside className="grid content-start gap-6">
      <section className="lg:sticky lg:top-6">
        <div className="flex items-center gap-4 lg:block">
          <img
            alt=""
            className="size-24 rounded-full bg-[var(--ui-bg-subtle)] object-cover ring-1 ring-[var(--ui-border)] lg:size-28"
            decoding="async"
            referrerPolicy="no-referrer"
            src={profile.avatar || avatarPlaceholder}
          />
          <div className="min-w-0 lg:mt-4">
            <h2 className="truncate text-xl font-semibold tracking-normal text-[var(--ui-text)]">{profile.nickname}</h2>
            <p className="mt-1 truncate text-sm text-[var(--ui-text-muted)]">{profile.email}</p>
          </div>
        </div>

        <div className="mt-5 grid gap-2">
          <Button asChild className="w-full" disabled={isUploading} variant="secondary">
            <label className="cursor-pointer">
              <input
                accept="image/jpeg,image/png,image/webp"
                className="sr-only"
                disabled={isUploading}
                type="file"
                onChange={(event) => void selectAvatar(event)}
              />
              <Upload className="size-4" />
              {isUploading ? t('me.uploading') : t('settings.uploadAvatar')}
            </label>
          </Button>
        </div>

        <div className="mt-6 border-t border-[var(--ui-border)] pt-5">
          <h2 className="text-sm font-semibold text-[var(--ui-text)]">{t('settings.security')}</h2>
        </div>
        <div className="mt-4 grid gap-2">
          <Button asChild variant="secondary">
            <Link to={routes.resetPassword}>
              <KeyRound className="size-4" />
              {t('settings.changePassword')}
            </Link>
          </Button>
          <Button disabled={sessionBusy} type="button" variant="ghost" onClick={() => void onSignOut()}>
            <LogOut className="size-4" />
            {t('settings.signOut')}
          </Button>
        </div>
      </section>

      {avatarDraft ? (
        <AvatarCropDialog
          draft={avatarDraft}
          isUploading={isUploading}
          onClose={() => {
            replaceAvatarDraft(null);
          }}
          onError={(error) => {
            onError(getErrorMessage(error, t('common.requestFailed')));
          }}
          onUpload={uploadAvatar}
        />
      ) : null}
    </aside>
  );
}
