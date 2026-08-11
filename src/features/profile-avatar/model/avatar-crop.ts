export type AvatarDraft = {
  file: File;
  url: string;
  width: number;
  height: number;
};

export type AvatarOffset = {
  x: number;
  y: number;
};

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export function clampAvatarOffset(offset: AvatarOffset): AvatarOffset {
  return {
    x: clamp(offset.x, -1, 1),
    y: clamp(offset.y, -1, 1),
  };
}

export function getAvatarCropGeometry(width: number, height: number, zoom: number, offset: AvatarOffset) {
  const sourceSize = Math.min(width, height) / clamp(zoom, 1, 2);
  const maxSourceX = width - sourceSize;
  const maxSourceY = height - sourceSize;
  const normalizedOffset = clampAvatarOffset(offset);
  const sourceX = clamp(maxSourceX / 2 + normalizedOffset.x * (maxSourceX / 2), 0, maxSourceX);
  const sourceY = clamp(maxSourceY / 2 + normalizedOffset.y * (maxSourceY / 2), 0, maxSourceY);
  return { sourceSize, sourceX, sourceY };
}

export function loadAvatarImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    const clearHandlers = () => {
      image.onload = null;
      image.onerror = null;
    };
    image.decoding = 'async';
    image.onload = () => {
      clearHandlers();
      resolve(image);
    };
    image.onerror = () => {
      clearHandlers();
      reject(new Error('Unable to load image.'));
    };
    image.src = src;
  });
}

export async function createSquareAvatarFile(file: File, sourceUrl: string, zoom: number, offset: AvatarOffset) {
  const image = await loadAvatarImage(sourceUrl);
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
      (result) => {
        if (result) resolve(result);
        else reject(new Error('Unable to crop image.'));
      },
      'image/webp',
      0.92,
    );
  });
  return new File([blob], `${file.name.replace(/\.[^.]+$/u, '') || 'avatar'}-cropped.webp`, {
    type: 'image/webp',
  });
}
