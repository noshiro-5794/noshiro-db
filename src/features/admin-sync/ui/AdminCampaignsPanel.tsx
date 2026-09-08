import { Pause, Play, RefreshCw, X } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { syncMutations, syncQueries, syncQueryKeys } from '../model/sync-queries';
import type { SyncCampaign, SyncCampaignStatus } from '@/shared/api';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { ListSurface } from '@/shared/ui/DataView';
import { cn } from '@/shared/lib/cn';

const activeStatuses = new Set<SyncCampaignStatus>([
  'queued',
  'discovering',
  'fetching',
  'mapping',
  'normalizing',
  'reconciling',
  'enriching',
  'reviewing',
]);

function campaignStatusVariant(status: SyncCampaignStatus): 'accent' | 'danger' | 'success' | 'secondary' {
  if (status === 'failed' || status === 'cancelled') return 'danger';
  if (status === 'completed' || status === 'succeeded') return 'success';
  if (activeStatuses.has(status)) return 'accent';
  return 'secondary';
}

function campaignPercent(campaign: SyncCampaign) {
  const percent = campaign.progress.percent;
  if (percent === null) return campaign.status === 'completed' ? 100 : 0;
  return Math.max(0, Math.min(100, percent));
}

export function AdminCampaignsPanel() {
  const queryClient = useQueryClient();
  const campaignsQuery = useQuery(syncQueries.campaigns());
  const summaryQuery = useQuery(syncQueries.campaignSummary());
  const actionMutation = useMutation(syncMutations.campaignAction());

  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: syncQueryKeys.campaigns() }),
      queryClient.invalidateQueries({ queryKey: syncQueryKeys.campaignSummary() }),
    ]);
  }

  async function runAction(campaign: SyncCampaign, action: 'pause' | 'resume' | 'cancel') {
    await actionMutation.mutateAsync({ campaignId: campaign.id, action });
    await refresh();
  }

  const campaigns = campaignsQuery.data ?? [];
  const summary = summaryQuery.data;

  return (
    <section
      aria-labelledby="admin-campaigns-title"
      className="grid gap-3 rounded-sm border border-border bg-surface p-4"
      data-slot="admin-campaigns-panel"
    >
      <header className="flex min-w-0 flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="m-0 text-sm font-semibold leading-5 text-foreground" id="admin-campaigns-title">
            Provider campaigns
          </h2>
          <p className="m-0 mt-0.5 text-xs leading-5 text-muted-foreground">
            Durable provider-wide synchronization and AI phases.
          </p>
        </div>
        <Button
          disabled={campaignsQuery.isFetching}
          size="sm"
          type="button"
          variant="secondary"
          onClick={() => void refresh()}
        >
          <RefreshCw className={cn('size-4', campaignsQuery.isFetching && 'animate-spin')} />
          Refresh
        </Button>
      </header>

      {summary ? (
        <dl className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-3 lg:grid-cols-6" data-slot="admin-campaign-summary">
          {[
            ['Running campaigns', String(summary.campaigns_by_status['fetching'] ?? 0)],
            ['Queued work items', String(summary.queued_items)],
            ['Failed work items', String(summary.failed_items)],
            ['Stale leases', String(summary.stale_leases)],
            ['Pending AI claims', String(summary.pending_ai_claims)],
          ].map(([label, value]) => (
            <div className="grid gap-0.5 rounded-sm bg-muted px-3 py-2" key={label}>
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="m-0 text-sm font-semibold tabular-nums text-foreground">{value}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {campaigns.length === 0 ? (
        <p className="m-0 text-xs text-muted-foreground">
          {campaignsQuery.isLoading ? 'Loading…' : 'No campaigns yet.'}
        </p>
      ) : (
        <ListSurface data-slot="admin-campaign-list">
          {campaigns.map((campaign) => {
            const percent = campaignPercent(campaign);
            const canPause = activeStatuses.has(campaign.status);
            const canResume = campaign.status === 'paused';
            const canCancel = campaign.status !== 'completed' && campaign.status !== 'cancelled';
            const isPending = actionMutation.isPending && actionMutation.variables.campaignId === campaign.id;

            return (
              <article
                className="grid min-w-0 gap-3 border-b border-border-subtle px-3 py-3 last:border-b-0 sm:px-4"
                data-slot="admin-campaign-row"
                key={campaign.id}
              >
                <header className="flex min-w-0 flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <h3 className="m-0 truncate text-[13px] font-semibold leading-5 text-foreground">
                        {campaign.provider_slug} · {campaign.campaign_type}
                      </h3>
                      <Badge variant={campaignStatusVariant(campaign.status)}>{campaign.status}</Badge>
                      <Badge variant="secondary">{campaign.ai_mode}</Badge>
                    </div>
                    <p className="m-0 mt-0.5 truncate text-xs text-muted-foreground">{campaign.error || campaign.id}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    {canPause ? (
                      <Button
                        disabled={isPending}
                        size="sm"
                        type="button"
                        variant="secondary"
                        onClick={() => void runAction(campaign, 'pause')}
                      >
                        <Pause className="size-4" /> Pause
                      </Button>
                    ) : null}
                    {canResume ? (
                      <Button
                        disabled={isPending}
                        size="sm"
                        type="button"
                        variant="secondary"
                        onClick={() => void runAction(campaign, 'resume')}
                      >
                        <Play className="size-4" /> Resume
                      </Button>
                    ) : null}
                    {canCancel ? (
                      <Button
                        disabled={isPending}
                        size="sm"
                        type="button"
                        variant="secondary"
                        onClick={() => void runAction(campaign, 'cancel')}
                      >
                        <X className="size-4" /> Cancel
                      </Button>
                    ) : null}
                  </div>
                </header>

                <div className="grid gap-1.5">
                  <div
                    aria-label={`${campaign.provider_slug}: ${percent}%`}
                    aria-valuemax={100}
                    aria-valuemin={0}
                    aria-valuenow={percent}
                    className="h-1 overflow-hidden rounded-[2px] bg-muted"
                    role="progressbar"
                  >
                    <div
                      className="h-full bg-brand transition-[width] duration-[var(--ui-transition-fast)]"
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                    <span className="tabular-nums">
                      {campaign.processed_items} / {campaign.total_items} processed · {percent}%
                    </span>
                    <span className="tabular-nums">
                      {campaign.progress.running} running · {campaign.progress.queued} queued ·{' '}
                      {campaign.progress.failed} failed
                      {campaign.progress.eta_seconds !== null ? ` · ETA ${campaign.progress.eta_seconds}s` : ''}
                    </span>
                  </div>
                </div>
              </article>
            );
          })}
        </ListSurface>
      )}
    </section>
  );
}
