import type { ISODateString, UUID } from './common';
import type { Collection, CollectionItem, Review } from './library';
import type { SubjectSummary } from './subject';
import type { PublicUserSummary } from './user';

export type ActivityType =
  | 'post_created'
  | 'user_subject_created'
  | 'user_subject_updated'
  | 'review_created'
  | 'collection_created'
  | 'collection_item_added'
  | 'comment_created'
  | 'user_followed'
  | (string & {});

export type CommunityVisibility = 'public' | 'followers' | 'private' | (string & {});

type CommunityFeedPolicy = 'hidden' | 'normal' | 'featured' | (string & {});

type CommunityPostType = 'status' | 'subject' | (string & {});

export type CommunityTargetType = 'activity' | 'post' | 'comment' | 'review' | 'collection' | (string & {});

export type CommunityReactionType = 'like' | (string & {});

export type CommunityReportReason = 'spam' | 'harassment' | 'spoiler' | 'illegal' | 'other' | (string & {});

export type CommunityReportStatus = 'pending' | 'accepted' | 'rejected' | (string & {});

export type CommunityPostSummary = {
  id: number;
  post_type?: CommunityPostType;
  content: string;
  visibility: CommunityVisibility;
  feed_policy?: CommunityFeedPolicy;
  is_spoiler: boolean;
  is_nsfw: boolean;
  is_pinned?: boolean;
  is_locked?: boolean;
  reply_count?: number;
  reaction_count?: number;
  last_activity_at?: ISODateString;
  created_at?: ISODateString;
  updated_at?: ISODateString;
  author?: PublicUserSummary | null;
  subject?: Pick<SubjectSummary, 'id' | 'title' | 'title_cn' | 'subject_type' | 'image_thumbnail' | 'nsfw'> | null;
  viewer_state?: {
    has_liked: boolean;
    has_bookmarked: boolean;
    is_following_author: boolean;
  };
};

export type CommunityCommentSummary = {
  id: number;
  parent_id?: number | null;
  target?: {
    type: CommunityTargetType;
    id: number;
  } | null;
  content: string;
  visibility: CommunityVisibility;
  is_spoiler: boolean;
  is_hidden?: boolean;
  is_locked?: boolean;
  reply_count?: number;
  reaction_count?: number;
  created_at?: ISODateString;
  updated_at?: ISODateString;
  author?: PublicUserSummary | null;
  viewer_state?: {
    has_liked: boolean;
    is_following_author: boolean;
  };
};

export type Activity = {
  id: number;
  activity_type: ActivityType;
  created_at: ISODateString;
  reaction_count?: number;
  reply_count?: number;
  message?: string;
  visibility?: CommunityVisibility;
  feed_policy?: CommunityFeedPolicy;
  group_key?: string;
  dedupe_key?: string;
  user?: PublicUserSummary | null;
  subject?: SubjectSummary;
  review?: Review;
  collection?: Collection;
  collection_item?: CollectionItem;
  post?: CommunityPostSummary;
  comment?: CommunityCommentSummary;
  target_user?: PublicUserSummary | null;
  viewer_state?: {
    has_liked: boolean;
  };
};

export type CommunityReaction = {
  id: number;
  target_type: CommunityTargetType;
  target_id: number;
  reaction_type: CommunityReactionType;
  created_at: ISODateString;
};

export type CommunityBookmark = {
  id: number;
  target_type: CommunityTargetType;
  target_id: number;
  target?: {
    type: 'post' | 'review' | 'collection' | (string & {});
    id: number;
    title?: string;
    body?: string;
    author?: PublicUserSummary | null;
    subject?: Pick<SubjectSummary, 'id' | 'title' | 'title_cn' | 'subject_type' | 'image_thumbnail'> | null;
    is_spoiler?: boolean;
    simple_rating?: number | null;
    created_at?: ISODateString;
  } | null;
  created_at: ISODateString;
};

export type CommunityNotification = {
  id: number;
  notification_type: string;
  actor: PublicUserSummary | null;
  target: {
    type: CommunityTargetType;
    id: number;
    author?: PublicUserSummary | null;
    owner?: PublicUserSummary | null;
    user?: PublicUserSummary | null;
    target_user?: PublicUserSummary | null;
    parent_id?: number | null;
    post?: {
      type: 'post';
      id: number;
      author?: PublicUserSummary | null;
    };
    review?: {
      type: 'review';
      id: number;
      author?: PublicUserSummary | null;
    };
    collection?: {
      type: 'collection';
      id: number;
      owner?: PublicUserSummary | null;
    };
    activity?: {
      type: 'activity';
      id: number;
      user?: PublicUserSummary | null;
    };
    subject?: {
      id: UUID;
    };
    comment?: {
      type: 'comment';
      id: number;
    };
  } | null;
  metadata: Record<string, unknown>;
  is_read: boolean;
  read_at: ISODateString | null;
  created_at: ISODateString;
};

export type CommunityNotificationUnreadCount = {
  unread_count: number;
};

export type CommunityNotificationReadAllResult = {
  updated_count: number;
};

export type CommunityRelationship = {
  user: PublicUserSummary;
  reason: string;
  created_at: ISODateString;
};

export type CommunityReport = {
  id: number;
  reason: CommunityReportReason;
  description: string;
  status: CommunityReportStatus;
  reporter: PublicUserSummary;
  reported_user: PublicUserSummary | null;
  target: {
    type: CommunityTargetType;
    id: number;
  } | null;
  resolved_by: PublicUserSummary | null;
  resolved_at: ISODateString | null;
  created_at: ISODateString;
};
