import { api, decodeCursorPage, encodePath } from '@/shared/api';
import type {
  ApiRequestContext,
  CursorPage,
  ImportJob,
  ImportJobCreate,
  SyncCampaign,
  SyncCampaignAction,
  SyncCampaignSummary,
} from '@/shared/api';
import {
  decodeImportJob,
  decodeSyncCampaign,
  decodeSyncCampaignList,
  decodeSyncCampaignSummary,
} from './sync-decoders';

export const operationsApi = {
  listImportJobs: (
    query: { cursor?: string; page_size?: number; provider?: string; status?: string } = {},
    context: ApiRequestContext = {},
  ) =>
    api.get<CursorPage<ImportJob>>('/api/v1/operations/import-jobs/', {
      ...context,
      decode: (value) => decodeCursorPage(value, decodeImportJob),
      query,
    }),

  getImportJob: (jobId: string, context: ApiRequestContext = {}) =>
    api.get<ImportJob>(`/api/v1/operations/import-jobs/${encodePath(jobId)}/`, {
      ...context,
      decode: decodeImportJob,
    }),

  createImportJob: (body: ImportJobCreate) =>
    api.post<ImportJob, ImportJobCreate>('/api/v1/operations/import-jobs/', body, {
      decode: decodeImportJob,
    }),

  listCampaigns: (query: { provider?: string; status?: string } = {}, context: ApiRequestContext = {}) =>
    api.get<SyncCampaign[]>('/api/v1/operations/sync/', {
      ...context,
      decode: decodeSyncCampaignList,
      query,
    }),

  getCampaignSummary: (context: ApiRequestContext = {}) =>
    api.get<SyncCampaignSummary>('/api/v1/operations/sync/summary/', {
      ...context,
      decode: decodeSyncCampaignSummary,
    }),

  campaignAction: (campaignId: string, action: SyncCampaignAction) =>
    api.post<SyncCampaign>(`/api/v1/operations/sync/${encodePath(campaignId)}/${encodePath(action)}/`, undefined, {
      decode: decodeSyncCampaign,
    }),
};

export const syncApi = operationsApi;
