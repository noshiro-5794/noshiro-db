import { mutationOptions, queryOptions } from '@tanstack/react-query';
import { operationsApi } from '../api/sync-api';
import type { ImportJobCreate, SyncCampaignAction } from '@/shared/api';

export const syncQueryKeys = {
  all: ['sync'] as const,
  importJobs: () => [...syncQueryKeys.all, 'import-jobs'] as const,
  importJobList: (query: { cursor?: string; page_size?: number; provider?: string; status?: string } = {}) =>
    [...syncQueryKeys.importJobs(), 'list', query] as const,
  importJob: (jobId: string) => [...syncQueryKeys.importJobs(), 'detail', jobId] as const,
  campaigns: () => [...syncQueryKeys.all, 'campaigns'] as const,
  campaignList: (query: { provider?: string; status?: string } = {}) =>
    [...syncQueryKeys.campaigns(), 'list', query] as const,
  campaignSummary: () => [...syncQueryKeys.campaigns(), 'summary'] as const,
};

export const syncQueries = {
  importJobs: (query: { cursor?: string; page_size?: number; provider?: string; status?: string } = {}) =>
    queryOptions({
      queryKey: syncQueryKeys.importJobList(query),
      queryFn: ({ signal }) => operationsApi.listImportJobs(query, { signal }),
    }),

  importJob: (jobId: string) =>
    queryOptions({
      queryKey: syncQueryKeys.importJob(jobId),
      queryFn: ({ signal }) => operationsApi.getImportJob(jobId, { signal }),
    }),

  campaigns: (query: { provider?: string; status?: string } = {}) =>
    queryOptions({
      queryKey: syncQueryKeys.campaignList(query),
      queryFn: ({ signal }) => operationsApi.listCampaigns(query, { signal }),
    }),

  campaignSummary: () =>
    queryOptions({
      queryKey: syncQueryKeys.campaignSummary(),
      queryFn: ({ signal }) => operationsApi.getCampaignSummary({ signal }),
    }),
};

export const syncMutations = {
  createImportJob: () =>
    mutationOptions({
      mutationFn: (body: ImportJobCreate) => operationsApi.createImportJob(body),
    }),

  campaignAction: () =>
    mutationOptions({
      mutationFn: ({ campaignId, action }: { campaignId: string; action: SyncCampaignAction }) =>
        operationsApi.campaignAction(campaignId, action),
    }),
};
