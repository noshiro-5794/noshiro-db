import type { ISODateString } from './common';

export type PublicUserSummary = {
  id: number;
  nickname: string;
  avatar: string | null;
};

export type PublicUserProfile = PublicUserSummary & {
  bio: string;
  stats: {
    subject_count: number;
    review_count: number;
    collection_count: number;
    following_count: number;
    follower_count: number;
  };
  is_following: boolean;
};

export type FollowRelation = {
  user: PublicUserSummary;
  followed_at: ISODateString;
};
