import type { RatingDetail, UserSubjectContext, UserSubjectStatus } from '@/shared/api';
import type { UserSubjectWriteBody } from '@/entities/library';

const markStatuses = ['wish', 'doing', 'done', 'on_hold', 'drop'] as const;
const decimalRatingPattern = /^(?:10(?:\.0)?|[0-9](?:\.[0-9])?)$/u;

export type MarkStatus = (typeof markStatuses)[number];

export type MarkDraft = {
  status: MarkStatus;
  simpleRating: string;
  rating: string;
  comment: string;
  isPublic: boolean;
  tagText: string;
  ratingDetails: RatingDetail[];
};

export type ParsedMarkDraft = {
  body: Required<Pick<UserSubjectWriteBody, 'status' | 'simple_rating' | 'rating' | 'comment' | 'is_public'>>;
  tagNames: string[];
  ratingDetails: RatingDetail[];
};

export function isMarkStatus(value: UserSubjectStatus | undefined): value is MarkStatus {
  return markStatuses.some((status) => status === value);
}

export function createMarkDraft(context: UserSubjectContext | undefined): MarkDraft {
  const mark = context?.user_subject;
  return {
    status: isMarkStatus(mark?.status) ? mark.status : 'wish',
    simpleRating: mark?.simple_rating ? String(mark.simple_rating) : '',
    rating: mark?.rating ?? '',
    comment: mark?.comment ?? '',
    isPublic: mark?.is_public ?? true,
    tagText: (context?.tags ?? []).map((tag) => tag.name).join(', '),
    ratingDetails: context?.rating_details.length ? context.rating_details : [{ key: '', value: '' }],
  };
}

export function parseMarkDraft(draft: MarkDraft): ParsedMarkDraft | null {
  const simpleRating = draft.simpleRating ? Number(draft.simpleRating) : null;
  if (simpleRating !== null && (!Number.isInteger(simpleRating) || simpleRating < 1 || simpleRating > 5)) return null;

  const rating = draft.rating.trim();
  if (rating && !decimalRatingPattern.test(rating)) return null;
  if (draft.comment.length > 2_000) return null;

  const tagNames = [
    ...new Set(
      draft.tagText
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
    ),
  ];
  if (tagNames.length > 100 || tagNames.some((tag) => tag.length > 64)) return null;

  const ratingDetails = draft.ratingDetails
    .map((detail) => ({ key: detail.key.trim(), value: detail.value.trim() }))
    .filter((detail) => detail.key || detail.value);
  if (
    ratingDetails.length > 100 ||
    ratingDetails.some(
      (detail) => !detail.key || detail.key.length > 256 || !decimalRatingPattern.test(detail.value),
    ) ||
    new Set(ratingDetails.map((detail) => detail.key)).size !== ratingDetails.length
  ) {
    return null;
  }

  return {
    body: {
      status: draft.status,
      simple_rating: simpleRating,
      rating: rating || null,
      comment: draft.comment,
      is_public: draft.isPublic,
    },
    tagNames,
    ratingDetails,
  };
}
