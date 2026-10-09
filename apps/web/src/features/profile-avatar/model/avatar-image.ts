export const avatarMaxBytes = 10 * 1024 * 1024;
const avatarMaxDimension = 8192;
const avatarMaxPixels = 40_000_000;

const avatarMimeTypes = ['image/jpeg', 'image/png', 'image/webp'] as const;

export type AvatarMimeType = (typeof avatarMimeTypes)[number];
export type AvatarImageErrorCode = 'invalid-content' | 'invalid-dimensions' | 'too-large' | 'unsupported-type';

export class AvatarImageError extends Error {
  readonly code: AvatarImageErrorCode;

  constructor(code: AvatarImageErrorCode) {
    super(code);
    this.name = 'AvatarImageError';
    this.code = code;
  }
}

function isAvatarMimeType(value: string): value is AvatarMimeType {
  return avatarMimeTypes.some((mimeType) => mimeType === value);
}

function hasBytes(bytes: Uint8Array, expected: readonly number[], offset = 0) {
  return expected.every((value, index) => bytes[offset + index] === value);
}

function detectMimeType(bytes: Uint8Array): AvatarMimeType | null {
  if (hasBytes(bytes, [0xff, 0xd8, 0xff])) {
    return 'image/jpeg';
  }
  if (hasBytes(bytes, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) {
    return 'image/png';
  }
  if (hasBytes(bytes, [0x52, 0x49, 0x46, 0x46]) && hasBytes(bytes, [0x57, 0x45, 0x42, 0x50], 8)) {
    return 'image/webp';
  }
  return null;
}

export async function validateAvatarFile(file: File) {
  if (!isAvatarMimeType(file.type)) {
    throw new AvatarImageError('unsupported-type');
  }
  if (file.size <= 0 || file.size > avatarMaxBytes) {
    throw new AvatarImageError('too-large');
  }

  const signature = new Uint8Array(await file.slice(0, 16).arrayBuffer());
  if (detectMimeType(signature) !== file.type) {
    throw new AvatarImageError('invalid-content');
  }
}

export function validateAvatarDimensions(width: number, height: number) {
  if (
    !Number.isInteger(width) ||
    !Number.isInteger(height) ||
    width <= 0 ||
    height <= 0 ||
    width > avatarMaxDimension ||
    height > avatarMaxDimension ||
    width * height > avatarMaxPixels
  ) {
    throw new AvatarImageError('invalid-dimensions');
  }
}
