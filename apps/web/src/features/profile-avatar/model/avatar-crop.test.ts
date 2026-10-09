import { describe, expect, it } from 'vitest';
import { clampAvatarOffset, getAvatarCropGeometry } from './avatar-crop';

describe('avatar crop geometry', () => {
  it('centers a square crop within a landscape image', () => {
    expect(getAvatarCropGeometry(1200, 800, 1, { x: 0, y: 0 })).toEqual({
      sourceSize: 800,
      sourceX: 200,
      sourceY: 0,
    });
  });

  it('applies zoom and normalized offsets without leaving the source image', () => {
    expect(getAvatarCropGeometry(1200, 800, 2, { x: 1, y: -1 })).toEqual({
      sourceSize: 400,
      sourceX: 800,
      sourceY: 0,
    });
    expect(clampAvatarOffset({ x: 4, y: -3 })).toEqual({ x: 1, y: -1 });
  });
});
