import { describe, expect, it } from 'vitest';
import {
  decodeAccessTokenPayload,
  decodeAvatarUpload,
  decodeCurrentUserProfile,
  decodeProfileStats,
} from './session-decoders';

describe('session response decoders', () => {
  it('accepts a valid access token and rejects empty or malformed tokens', () => {
    expect(decodeAccessTokenPayload({ access: 'token' })).toEqual({ access: 'token' });
    expect(() => decodeAccessTokenPayload({ access: ' ' })).toThrow(TypeError);
    expect(() => decodeAccessTokenPayload({ access: 42 })).toThrow(TypeError);
  });

  it('accepts only a non-empty avatar URL', () => {
    expect(decodeAvatarUpload({ avatar: '/media/avatars/user.webp', ignored: true })).toEqual({
      avatar: '/media/avatars/user.webp',
    });
    expect(() => decodeAvatarUpload({ avatar: '' })).toThrow(TypeError);
    expect(() => decodeAvatarUpload({ avatar: 42 })).toThrow(TypeError);
  });

  it('normalizes a valid current-user profile to the trusted contract', () => {
    expect(
      decodeCurrentUserProfile({
        user_id: 42,
        email: 'user@example.com',
        is_staff: false,
        is_superuser: false,
        nickname: 'User',
        avatar: null,
        bio: 'Hello',
        language: 'zh-CN',
        appearance: 'dark',
        theme_color: '#66ccff',
        show_adult_content: false,
        adult_content_confirmed_at: null,
        ignored_server_field: 'not propagated',
      }),
    ).toEqual({
      user_id: 42,
      email: 'user@example.com',
      is_staff: false,
      is_superuser: false,
      nickname: 'User',
      avatar: null,
      bio: 'Hello',
      language: 'zh-CN',
      appearance: 'dark',
      theme_color: '#66ccff',
      show_adult_content: false,
      adult_content_confirmed_at: null,
    });
  });

  it('rejects profiles with invalid privilege flags or preferences', () => {
    const base = {
      user_id: 42,
      email: 'user@example.com',
      is_staff: false,
      is_superuser: false,
      nickname: 'User',
      avatar: null,
      bio: '',
      language: null,
      appearance: null,
      theme_color: '',
      show_adult_content: false,
      adult_content_confirmed_at: null,
    };

    expect(() => decodeCurrentUserProfile({ ...base, is_staff: 'false' })).toThrow(TypeError);
    expect(() => decodeCurrentUserProfile({ ...base, user_id: '42' })).toThrow(TypeError);
    expect(() => decodeCurrentUserProfile({ ...base, appearance: 'sepia' })).toThrow(TypeError);
    expect(() => decodeCurrentUserProfile({ ...base, language: 'invalid' })).toThrow(TypeError);
  });
});

describe('profile stats decoder', () => {
  const stats = {
    year: 2026,
    available_years: [2026, 2025],
    totals: { subjects: 3, reviews: 2, collections: 1, marks_in_year: 3 },
    mark_calendar: [{ date: '2026-07-29', count: 2 }],
  };

  it('accepts valid non-negative profile statistics', () => {
    expect(decodeProfileStats(stats)).toEqual(stats);
  });

  it.each([
    { ...stats, year: 2026.5 },
    { ...stats, available_years: [2026, '2025'] },
    { ...stats, totals: { ...stats.totals, subjects: -1 } },
    { ...stats, mark_calendar: [{ date: '07/29/2026', count: 2 }] },
  ])('rejects malformed profile statistics', (value) => {
    expect(() => decodeProfileStats(value)).toThrow(TypeError);
  });
});
