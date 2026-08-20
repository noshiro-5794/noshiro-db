import type { DateString } from './common';

export type SendCodePurpose = 'register' | 'login' | 'reset_password';

export type AccessTokenPayload = {
  access: string;
};

export type CurrentUserProfile = {
  user_id: number;
  email: string;
  is_staff: boolean;
  is_superuser: boolean;
  nickname: string;
  avatar: string | null;
  bio: string;
  language: 'auto' | 'en-US' | 'zh-CN' | 'ja-JP' | null;
  appearance: 'auto' | 'light' | 'dark' | null;
  theme_color: string;
  show_adult_content: boolean;
  adult_content_confirmed_at: string | null;
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
