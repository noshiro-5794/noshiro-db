import { useEffect, useRef } from 'react';
import { CheckCircle2 } from 'lucide-react';

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
    };
  }
}

const scriptId = 'hcaptcha-api-script';

type HCaptchaBoxProps = {
  resetSignal: number;
  siteKey: string;
  onChange: (token: string) => void;
};

type CaptchaSentStatusProps = {
  detail: string;
  title: string;
};

export function CaptchaSentStatus({ detail, title }: CaptchaSentStatusProps) {
  return (
    <div className="auth-captcha-status" role="status">
      <span className="auth-captcha-status-icon" aria-hidden="true">
        <CheckCircle2 className="size-3.5" />
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-medium text-[var(--color-text)]">{title}</span>
        <span className="mt-0.5 block text-[11px] text-[var(--color-text-muted)]">{detail}</span>
      </span>
    </div>
  );
}

export function HCaptchaBox({ resetSignal, siteKey, onChange }: HCaptchaBoxProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const widgetIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!siteKey || !containerRef.current) {
      return;
    }

    function renderWidget() {
      if (!window.hcaptcha || !containerRef.current || widgetIdRef.current) {
        return;
      }
      widgetIdRef.current = window.hcaptcha.render(containerRef.current, {
        sitekey: siteKey,
        callback: onChange,
        'expired-callback': () => onChange(''),
        'error-callback': () => onChange(''),
      });
    }

    const existingScript = document.getElementById(scriptId) as HTMLScriptElement | null;
    if (existingScript) {
      if (window.hcaptcha) {
        renderWidget();
      } else {
        existingScript.addEventListener('load', renderWidget, { once: true });
      }
      return;
    }

    const script = document.createElement('script');
    script.id = scriptId;
    script.src = 'https://js.hcaptcha.com/1/api.js?render=explicit';
    script.async = true;
    script.defer = true;
    script.addEventListener('load', renderWidget, { once: true });
    document.head.appendChild(script);
  }, [onChange, siteKey]);

  useEffect(() => {
    if (widgetIdRef.current && window.hcaptcha) {
      window.hcaptcha.reset(widgetIdRef.current);
      onChange('');
    }
  }, [onChange, resetSignal]);

  if (!siteKey) {
    return null;
  }

  return (
    <div className="flex min-h-[78px] justify-center overflow-hidden rounded-xl">
      <div ref={containerRef} />
    </div>
  );
}
