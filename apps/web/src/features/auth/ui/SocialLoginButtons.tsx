import { useEffect, useState } from 'react';
import { socialApi, type SocialProvider } from '@/entities/session';
import { useI18n } from '@/shared/i18n';
import { getErrorMessage } from '@/shared/lib/error';
import { Button } from '@/shared/ui/Button';

/** The GitHub mark is a brand icon, so it ships as inline SVG, not from a set. */
function GitHubMark() {
  return (
    <svg aria-hidden="true" className="size-4 shrink-0" viewBox="0 0 16 16" fill="currentColor">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.4 7.4 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}

const providerLabelKey: Record<string, 'auth.continueWithGitHub' | undefined> = {
  github: 'auth.continueWithGitHub',
};

export function SocialLoginButtons({ redirect, onError }: { redirect: string; onError: (message: string) => void }) {
  const { t } = useI18n();
  const [providers, setProviders] = useState<SocialProvider[]>([]);
  const [isPending, setIsPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void socialApi
      .listProviders()
      .then((list) => {
        if (!cancelled) setProviders(list.filter((provider) => provider.enabled));
      })
      // A missing provider endpoint simply means no social buttons.
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  if (providers.length === 0) return null;

  async function start(provider: string) {
    setIsPending(true);
    try {
      const url = await socialApi.authorizeUrl(provider, redirect);
      window.location.assign(url);
    } catch (error) {
      setIsPending(false);
      onError(getErrorMessage(error, t('auth.socialFailed')));
    }
  }

  return (
    <div className="motion-rise motion-delay-1 grid gap-4">
      {providers.map((provider) => {
        const labelKey = providerLabelKey[provider.provider];
        if (!labelKey) return null;
        return (
          <Button
            disabled={isPending}
            key={provider.provider}
            size="lg"
            type="button"
            variant="secondary"
            onClick={() => void start(provider.provider)}
          >
            <GitHubMark />
            {t(labelKey)}
          </Button>
        );
      })}
      <div
        aria-hidden="true"
        className="flex items-center gap-3 text-[11px] uppercase tracking-wide text-[var(--ui-text-faint)]"
      >
        <span className="h-px flex-1 bg-[var(--ui-border-subtle)]" />
        {t('auth.orDivider')}
        <span className="h-px flex-1 bg-[var(--ui-border-subtle)]" />
      </div>
    </div>
  );
}
