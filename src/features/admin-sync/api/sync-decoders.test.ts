import { describe, expect, it } from 'vitest';
import {
  decodeBangumiSubjectResult,
  decodeCalendarRunResult,
  decodeIncrementalRunResult,
  decodeIncrementalStatus,
  decodeSyncJobPage,
  decodeSyncCampaignList,
  decodeSyncCampaignSummary,
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

const campaign = {
  id: 'campaign-1',
  provider_slug: 'vndb',
  campaign_type: 'full',
  status: 'fetching',
  ai_mode: 'off',
  parameters: { page_size: 100 },
  total_items: 1000,
  processed_items: 120,
  synced_items: 110,
  skipped_items: 5,
  failed_items: 5,
  quality_report: null,
  cost: null,
  error: '',
  heartbeat_at: '2026-07-29T00:00:00Z',
  next_run_at: null,
  created_at: '2026-07-29T00:00:00Z',
  started_at: '2026-07-29T00:00:00Z',
  finished_at: null,
  updated_at: '2026-07-29T00:00:00Z',
  progress: {
    percent: 12.5,
    queued: 800,
    running: 1,
    succeeded: 110,
    failed: 5,
    retry_waiting: 0,
    throughput_items_per_second: 2.25,
    eta_seconds: 391,
  },
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

  it('decodes campaign lists and summaries', () => {
    expect(decodeSyncCampaignList([campaign])).toHaveLength(1);
    expect(
      decodeSyncCampaignSummary({
        campaigns_by_status: { fetching: 1, paused: 2 },
        campaigns_by_provider: { vndb: 3 },
        stale_leases: 0,
        queued_items: 800,
        failed_items: 5,
        pending_ai_claims: 0,
      }),
    ).toMatchObject({ queued_items: 800 });
  });

  it('rejects malformed campaign responses', () => {
    expect(() => decodeSyncCampaignList([{ ...campaign, status: 3 }])).toThrow(TypeError);
    expect(() => decodeSyncCampaignSummary({ campaigns_by_status: { fetching: 'x' } })).toThrow(TypeError);
  });

  it.each([{}, { task_id: 1, status: 'queued' }, { results: [{ ...incrementalResult, failed_count: '0' }] }])(
    'rejects malformed mutation responses',
    (value) => {
      expect(() => decodeIncrementalRunResult(value)).toThrow(TypeError);
    },
  );
});
