import { type PointerEvent, useState } from 'react';
import { Crop, Upload } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { Slider } from '@/shared/ui/Slider';
import {
  clampAvatarOffset,
  createSquareAvatarFile,
  getAvatarCropGeometry,
  type AvatarDraft,
  type AvatarOffset,
} from '../model/avatar-crop';

type AvatarDragState = {
  pointerId: number;
  startX: number;
  startY: number;
  offset: AvatarOffset;
  previewWidth: number;
  previewHeight: number;
};

type AvatarCropDialogProps = {
  draft: AvatarDraft;
  isUploading: boolean;
  onClose: () => void;
  onError: (error: unknown) => void;
  onUpload: (file: File) => Promise<void>;
};

export function AvatarCropDialog({ draft, isUploading, onClose, onError, onUpload }: AvatarCropDialogProps) {
  const { t } = useI18n();
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState<AvatarOffset>({ x: 0, y: 0 });
  const [drag, setDrag] = useState<AvatarDragState | null>(null);
  const geometry = getAvatarCropGeometry(draft.width, draft.height, zoom, offset);

  function updateOffset(nextOffset: AvatarOffset) {
    setOffset(clampAvatarOffset(nextOffset));
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    const previewRect = event.currentTarget.parentElement?.getBoundingClientRect();
    event.currentTarget.setPointerCapture(event.pointerId);
    setDrag({
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      offset,
      previewWidth: previewRect?.width || 1,
      previewHeight: previewRect?.height || 1,
    });
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!drag || drag.pointerId !== event.pointerId) return;
    const startGeometry = getAvatarCropGeometry(draft.width, draft.height, zoom, drag.offset);
    const maxSourceX = draft.width - startGeometry.sourceSize;
    const maxSourceY = draft.height - startGeometry.sourceSize;
    const deltaSourceX = (event.clientX - drag.startX) * (draft.width / drag.previewWidth);
    const deltaSourceY = (event.clientY - drag.startY) * (draft.height / drag.previewHeight);
    updateOffset({
      x: maxSourceX > 0 ? drag.offset.x + deltaSourceX / (maxSourceX / 2) : 0,
      y: maxSourceY > 0 ? drag.offset.y + deltaSourceY / (maxSourceY / 2) : 0,
    });
  }

  function handlePointerUp(event: PointerEvent<HTMLDivElement>) {
    if (drag?.pointerId === event.pointerId) setDrag(null);
  }

  async function uploadCroppedAvatar() {
    try {
      const croppedFile = await createSquareAvatarFile(draft.file, draft.url, zoom, offset);
      await onUpload(croppedFile);
    } catch (error) {
      onError(error);
    }
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{t('settings.avatarDialogTitle')}</DialogTitle>
          <DialogDescription>{t('settings.avatarDialogDescription')}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-5">
          <div className="grid gap-4 sm:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
            <div
              className="relative mx-auto w-full max-w-80 overflow-hidden rounded-md bg-muted ring-1 ring-border"
              style={{ aspectRatio: `${draft.width} / ${draft.height}` }}
            >
              <img
                alt=""
                className="absolute inset-0 size-full select-none object-contain"
                decoding="async"
                draggable={false}
                src={draft.url}
              />
              <div
                className={`absolute touch-none rounded-md border-2 border-white shadow-[0_0_0_999px_rgb(0_0_0/0.28)] ring-1 ring-black/10 dark:ring-white/20 ${drag ? 'cursor-grabbing' : 'cursor-grab'}`}
                role="application"
                aria-label={t('settings.avatarCropFrame')}
                style={{
                  left: `${(geometry.sourceX / draft.width) * 100}%`,
                  top: `${(geometry.sourceY / draft.height) * 100}%`,
                  width: `${(geometry.sourceSize / draft.width) * 100}%`,
                  height: `${(geometry.sourceSize / draft.height) * 100}%`,
                }}
                onPointerCancel={handlePointerUp}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
              >
                <span className="pointer-events-none absolute inset-3 rounded-sm border border-white/60 dark:border-white/20" />
              </div>
            </div>
            <div className="grid content-center gap-4">
              <CropSlider label={t('settings.avatarZoom')} max={2} min={1} value={zoom} onChange={setZoom} />
              <CropSlider
                label={t('settings.avatarPositionX')}
                max={1}
                min={-1}
                value={offset.x}
                onChange={(value) => {
                  updateOffset({ ...offset, x: value });
                }}
              />
              <CropSlider
                label={t('settings.avatarPositionY')}
                max={1}
                min={-1}
                value={offset.y}
                onChange={(value) => {
                  updateOffset({ ...offset, y: value });
                }}
              />
              <div className="rounded-sm bg-muted px-3 py-2.5 text-[13px] leading-5 text-muted-foreground">
                {t('settings.avatarCropHint')}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button disabled={isUploading} type="button" variant="secondary" onClick={onClose}>
              {t('common.cancel')}
            </Button>
            <Button disabled={isUploading} type="button" variant="secondary" onClick={() => void onUpload(draft.file)}>
              <Upload className="size-4" />
              {t('settings.uploadOriginal')}
            </Button>
            <Button disabled={isUploading} type="button" onClick={() => void uploadCroppedAvatar()}>
              <Crop className="size-4" />
              {isUploading ? t('me.uploading') : t('settings.uploadCropped')}
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function CropSlider({
  label,
  max,
  min,
  onChange,
  value,
}: {
  label: string;
  max: number;
  min: number;
  onChange: (value: number) => void;
  value: number;
}) {
  return (
    <div className="grid gap-2">
      <div className="flex items-center justify-between gap-3 text-sm font-medium text-[var(--ui-text)]">
        <span>{label}</span>
        <span className="tabular-nums text-[var(--ui-text-subtle)]">{Math.round(value * 100)}</span>
      </div>
      <Slider aria-label={label} max={max} min={min} step={0.01} value={value} onValueChange={onChange} />
    </div>
  );
}
