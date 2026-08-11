import { describe, expect, it } from 'vitest';
import type { Activity } from '@/shared/api';
import { activityBody, activityTitle } from './activity-presentation';

const activity = (overrides: Partial<Activity>): Activity => ({
  id: 1,
  activity_type: 'post_created',
  created_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

describe('activity presentation', () => {
  it('uses the first meaningful content line for a title', () => {
    expect(
      activityTitle(
        activity({
          post: {
            id: 1,
            content: '\n  First line  \nSecond',
            visibility: 'public',
            is_spoiler: false,
            is_nsfw: false,
          },
        }),
        'Fallback',
      ),
    ).toBe('First line');
  });

  it('prefers explicit messages and falls back without leaking undefined text', () => {
    expect(activityBody(activity({ message: 'Changed status' }), 'Fallback')).toBe('Changed status');
    expect(activityBody(activity({}), 'Fallback')).toBe('Fallback');
  });
});
