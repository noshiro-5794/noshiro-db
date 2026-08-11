import { describe, expect, it } from 'vitest';
import { AvatarImageError, avatarMaxBytes, validateAvatarDimensions, validateAvatarFile } from './avatar-image';

function file(bytes: number[], type: string) {
  return new File([new Uint8Array(bytes)], 'avatar', { type });
}

describe('avatar image validation', () => {
  it.each([
    [[0xff, 0xd8, 0xff, 0xe0], 'image/jpeg'],
    [[0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a], 'image/png'],
    [[0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x45, 0x42, 0x50], 'image/webp'],
  ] as const)('accepts a valid %s signature', async (bytes, type) => {
    await expect(validateAvatarFile(file([...bytes], type))).resolves.toBeUndefined();
  });

  it('rejects unsupported declared MIME types', async () => {
    await expect(validateAvatarFile(file([0x47, 0x49, 0x46], 'image/gif'))).rejects.toMatchObject({
      code: 'unsupported-type',
    } satisfies Partial<AvatarImageError>);
  });

  it('rejects content whose signature does not match its declared MIME type', async () => {
    await expect(validateAvatarFile(file([0xff, 0xd8, 0xff], 'image/png'))).rejects.toMatchObject({
      code: 'invalid-content',
    } satisfies Partial<AvatarImageError>);
  });

  it('rejects empty and oversized files', async () => {
    await expect(validateAvatarFile(new File([], 'empty.png', { type: 'image/png' }))).rejects.toMatchObject({
      code: 'too-large',
    } satisfies Partial<AvatarImageError>);
    const oversized = new File([new Uint8Array(avatarMaxBytes + 1)], 'large.jpg', { type: 'image/jpeg' });
    await expect(validateAvatarFile(oversized)).rejects.toMatchObject({
      code: 'too-large',
    } satisfies Partial<AvatarImageError>);
  });

  it('accepts bounded dimensions', () => {
    expect(() => {
      validateAvatarDimensions(512, 512);
    }).not.toThrow();
    expect(() => {
      validateAvatarDimensions(8000, 5000);
    }).not.toThrow();
  });

  it.each([
    [0, 512],
    [512.5, 512],
    [8193, 100],
    [8000, 6000],
  ])('rejects unsafe dimensions %i x %i', (width, height) => {
    expect(() => {
      validateAvatarDimensions(width, height);
    }).toThrow(AvatarImageError);
  });
});
