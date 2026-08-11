import { useEffect, useRef, useState } from 'react';
import { CheckCircle2, RotateCcw } from 'lucide-react';
import { Button } from '@/shared/ui/Button';

declare global {
  interface Window {
    hcaptcha?: {
      render: (
        container: HTMLElement,
        options: {
          sitekey: string;
          callback: (token: string) => void;
          'expired-callback': () => void;
          'error-callback': () => void;
        },
      ) => string;
      reset: (widgetId?: string) => void;
      remove: (widgetId?: string) => void;
    };
  }
}

const scriptId = 'hcaptcha-api-script';

type HCaptchaBoxProps = {
  resetSignal: number;
  retryLabel: string;
  siteKey: string;
  onChange: (token: string) => void;
  onError: () => void;
};

type CaptchaSentStatusProps = {
  detail: string;
  title: string;
};

export function CaptchaSentStatus({ detail, title }: CaptchaSentStatusProps) {
  return (
    <div
      className="flex min-h-14 items-center gap-3 rounded-sm border border-border px-3.5 py-2.5 text-foreground"
      role="status"
    >
      <span
        className="grid size-6 shrink-0 place-items-center rounded-full text-[color-mix(in_srgb,var(--ui-accent-text)_72%,var(--ui-text-muted))]"
        aria-hidden="true"
      >
        <CheckCircle2 className="size-3.5" />
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-medium text-[var(--ui-text)]">{title}</span>
        <span className="mt-0.5 block text-[11px] text-[var(--ui-text-muted)]">{detail}</span>
      </span>
    </div>
  );
}

export function HCaptchaBox({ resetSignal, retryLabel, siteKey, onChange, onError }: HCaptchaBoxProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const widgetIdRef = useRef<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!siteKey || !containerRef.current) {
      return;
    }

    const container = containerRef.current;
    let active = true;
    let loadTimeoutId: number | undefined;

    function clearLoadTimeout() {
      if (loadTimeoutId !== undefined) window.clearTimeout(loadTimeoutId);
      loadTimeoutId = undefined;
    }

    function reportFailure() {
      if (!active) return;
      clearLoadTimeout();
      onChange('');
      onError();
      setFailed(true);
      if (!window.hcaptcha) document.getElementById(scriptId)?.remove();
    }

    function renderWidget() {
      if (!active || !window.hcaptcha || widgetIdRef.current) {
        return;
      }
      clearLoadTimeout();
      try {
        widgetIdRef.current = window.hcaptcha.render(container, {
          sitekey: siteKey,
          callback: (token) => {
            setFailed(false);
            onChange(token);
          },
          'expired-callback': () => {
            onChange('');
          },
          'error-callback': reportFailure,
        });
        setFailed(false);
      } catch {
        reportFailure();
      }
    }

    function handleScriptLoad(event: Event) {
      if (event.currentTarget instanceof HTMLScriptElement) event.currentTarget.dataset['loaded'] = 'true';
      if (window.hcaptcha) renderWidget();
      else reportFailure();
    }

    const existingScript = document.getElementById(scriptId) as HTMLScriptElement | null;
    if (existingScript) {
      if (window.hcaptcha) {
        renderWidget();
      } else if (existingScript.dataset['loaded'] === 'true') {
        reportFailure();
      } else {
        existingScript.addEventListener('load', handleScriptLoad);
        existingScript.addEventListener('error', reportFailure);
        loadTimeoutId = window.setTimeout(reportFailure, 15_000);
      }
    } else {
      const script = document.createElement('script');
      script.id = scriptId;
      script.src = 'https://js.hcaptcha.com/1/api.js?render=explicit';
      script.async = true;
      script.defer = true;
      script.addEventListener('load', handleScriptLoad);
      script.addEventListener('error', reportFailure);
      document.head.appendChild(script);
      loadTimeoutId = window.setTimeout(reportFailure, 15_000);
    }

    return () => {
      active = false;
      clearLoadTimeout();
      const script = document.getElementById(scriptId);
      script?.removeEventListener('load', handleScriptLoad);
      script?.removeEventListener('error', reportFailure);

      if (widgetIdRef.current && window.hcaptcha) {
        try {
          window.hcaptcha.remove(widgetIdRef.current);
        } catch {
          container.replaceChildren();
        }
      }
      widgetIdRef.current = null;
    };
  }, [attempt, onChange, onError, siteKey]);

  useEffect(() => {
    if (widgetIdRef.current && window.hcaptcha) {
      try {
        window.hcaptcha.reset(widgetIdRef.current);
        onChange('');
      } catch {
        setFailed(true);
        onChange('');
        onError();
      }
    }
  }, [onChange, onError, resetSignal]);

  if (!siteKey) {
    return null;
  }

  return (
    <div className="grid min-h-[78px] place-items-center overflow-hidden rounded-sm">
      <div className={failed ? 'hidden' : ''} ref={containerRef} />
      {failed ? (
        <Button
          type="button"
          variant="secondary"
          onClick={() => {
            setAttempt((value) => value + 1);
          }}
        >
          <RotateCcw className="size-4" />
          {retryLabel}
        </Button>
      ) : null}
    </div>
  );
}
