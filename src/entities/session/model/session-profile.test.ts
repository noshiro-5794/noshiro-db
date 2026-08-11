import { describe, expect, it } from 'vitest';
import type { CurrentUserProfile } from './session';
import { patchSessionProfile } from './session-profile';

const profile: CurrentUserProfile = {
  user_id: 1,
  email: 'noshiro@example.com',
  nickname: 'Noshiro',
  avatar: null,
  bio: '',
  is_staff: false,
  is_superuser: false,
  language: 'en-US',
  appearance: 'light',
};

describe('patchSessionProfile', () => {
  it('merges concurrent mutation results without reverting unrelated fields', () => {
    const renamed = patchSessionProfile(profile, { nickname: 'Noshiro Kai' });
    const withAvatar = patchSessionProfile(renamed, { avatar: '/media/avatar.webp' });

    expect(withAvatar).toMatchObject({
      nickname: 'Noshiro Kai',
      avatar: '/media/avatar.webp',
      language: 'en-US',
    });
  });

  it('does not recreate a profile after the session has been cleared', () => {
    expect(patchSessionProfile(null, { avatar: '/media/avatar.webp' })).toBeNull();
  });
});
