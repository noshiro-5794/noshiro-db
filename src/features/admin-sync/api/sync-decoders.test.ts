import { describe, expect, it } from 'vitest';
import {
  decodeBangumiSubjectResult,
  decodeCalendarRunResult,
  decodeIncrementalRunResult,
  decodeIncrementalStatus,
  decodeSyncJobPage,
} from './sync-decoders';

const incrementalResult = {
  task_name: 'incremental_subject',
  shard: 'default',
  start_id: 1,
  end_id: 10,
  processed_count: 10,
  synced_count: 8,
  skipped_count: 2,
  failed_count: 0,
};

describe('administrator sync response decoders', () => {
  it('decodes queued and synchronous mutation responses', () => {
    expect(
      decodeBangumiSubjectResult({ task_id: 'task', status: 'queued', job_id: 'job', bangumi_id: 456 }),
    ).toMatchObject({ task_id: 'task', bangumi_id: 456 });
    expect(decodeIncrementalRunResult({ results: [incrementalResult] })).toEqual({ results: [incrementalResult] });
    expect(
      decodeCalendarRunResult({
        weekday_count: 7,
        item_count: 20,
        synced_subject_count: 10,
        failed_subject_count: 0,
        detail_synced_count: 9,
        detail_failed_count: 1,
      }),
    ).toMatchObject({ weekday_count: 7 });
  });

  it('decodes status and job pagination only when their nested shapes are valid', () => {
    expect(
      decodeIncrementalStatus({
        tasks: [
          {
            task_name: 'incremental_subject',
            shard: 'default',
            current_id: 10,
            end_id: 20,
            status: 'idle',
            fail_count: 0,
            updated_at: '2026-07-29T00:00:00Z',
          },
        ],
      }).tasks,
    ).toHaveLength(1);

    expect(() => decodeSyncJobPage({ count: 1, next: null, previous: null, results: [{ id: 'job' }] })).toThrow(
      TypeError,
    );
  });

  it.each([{}, { task_id: 1, status: 'queued' }, { results: [{ ...incrementalResult, failed_count: '0' }] }])(
    'rejects malformed mutation responses',
    (value) => {
      expect(() => decodeIncrementalRunResult(value)).toThrow(TypeError);
    },
  );
});
