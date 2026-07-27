import type { DateString } from './common';

export type SendCodePurpose = 'register' | 'login' | 'reset_password';

export type AccessTokenPayload = {
  access: string;
};

export type CurrentUserProfile = {
  user_id: string;
  email: string;
  is_staff: boolean;
  is_superuser: boolean;
  nickname: string;
  avatar: string | null;
  bio?: string;
  language?: 'auto' | 'en-US' | 'zh-CN' | 'ja-JP';
  appearance?: 'auto' | 'light' | 'dark';
  theme_color: string | null;
};

export type ProfileStats = {
  year: number;
  available_years: number[];
  totals: {
    subjects: number;
    reviews: number;
    collections: number;
    marks_in_year: number;
  };
  mark_calendar: Array<{
    date: DateString;
    count: number;
  }>;
};
