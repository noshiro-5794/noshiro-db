import { createContext } from 'react';
import type { CodeLoginInput, CurrentUserProfile, PasswordLoginInput, RegisterInput } from './session';
import type { SessionProfilePatch } from './session-profile';

export type AuthStatus = 'checking' | 'authenticated' | 'anonymous';
type UserRole = 'guest' | 'user' | 'admin';

export type AuthState = {
  profile: CurrentUserProfile | null;
  status: AuthStatus;
  role: UserRole;
  loading: boolean;
  isAuthenticated: boolean;
  loginWithPassword: (input: PasswordLoginInput) => Promise<void>;
  loginWithCode: (input: CodeLoginInput) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => Promise<void>;
  patchProfile: (patch: SessionProfilePatch) => void;
};

export const AuthContext = createContext<AuthState | null>(null);
