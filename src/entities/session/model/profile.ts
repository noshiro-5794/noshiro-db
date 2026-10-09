import type { CurrentUserProfile } from './session';

export type SessionProfilePatch = Partial<
  Pick<CurrentUserProfile, 'appearance' | 'avatar' | 'bio' | 'language' | 'nickname'>
>;

export function patchSessionProfile(profile: CurrentUserProfile | null, patch: SessionProfilePatch) {
  return profile ? { ...profile, ...patch } : profile;
}
