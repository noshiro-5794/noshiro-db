import { type FormEvent, useCallback, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { KeyRound, LockKeyhole, Mail } from 'lucide-react';
import { env } from '@/config/env';
import { authApi } from '@/features/auth/api';
import { CaptchaSentStatus, HCaptchaBox } from '@/features/auth/components/HCaptchaBox';
import { AuthField, AuthPageLayout } from '@/features/auth/components/AuthPageLayout';
import { useAuth } from '@/features/auth/use-auth';
import { formatCodeCooldownLabel, useCodeCooldown } from '@/features/auth/use-code-cooldown';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';
import { Button } from '@/shared/ui/Button';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function LoginPage() {
  const { t } = useI18n();
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const returnTo = typeof location.state?.returnTo === 'string' && location.state.returnTo.startsWith('/') ? location.state.returnTo : routes.home;
  const [mode, setMode] = useState<'password' | 'code'>('password');
  const [email, setEmail] = useState('');
  const [captchaToken, setCaptchaToken] = useState('');
  const [captchaResetSignal, setCaptchaResetSignal] = useState(0);
  const [isSendingCode, setIsSendingCode] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const { isCoolingDown, remainingSeconds, startCooldown } = useCodeCooldown(60);
  const handleCaptchaChange = useCallback((token: string) => setCaptchaToken(token), []);

  if (auth.isAuthenticated) {
    return <Navigate replace to={returnTo} />;
  }

  async function handleSendCode() {
    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setErrorMessage(t('auth.emailRequired'));
      return;
    }
    if (env.hcaptchaSiteKey && !captchaToken) {
      setErrorMessage(t('auth.captchaRequired'));
      return;
    }

    setIsSendingCode(true);
    setErrorMessage('');
    try {
      await authApi.sendCode({
        email: trimmedEmail,
        purpose: 'login',
        hcaptcha_token: captchaToken || undefined,
      });
      setCaptchaResetSignal((value) => value + 1);
      setCaptchaToken('');
      startCooldown();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, t('common.requestFailed')));
    } finally {
      setIsSendingCode(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const email = String(formData.get('email') ?? '').trim();

    setErrorMessage('');
    try {
      if (mode === 'password') {
        const password = String(formData.get('password') ?? '');
        await auth.loginWithPassword({ email, password });
      } else {
        const code = String(formData.get('code') ?? '').trim();
        await auth.loginWithCode({ email, code });
      }
      navigate(returnTo, { replace: true });
    } catch (error) {
      setErrorMessage(getErrorMessage(error, t('common.requestFailed')));
    }
  }

  return (
    <AuthPageLayout>
      <form
        className="grid gap-5"
        onSubmit={handleSubmit}
      >
        <div className="motion-rise grid justify-items-center text-center">
          <img
            className="size-12 rounded-2xl"
            src="/brand/icon.svg"
            alt=""
            aria-hidden="true"
          />
          <h1 className="mt-5 text-2xl font-semibold tracking-tight text-neutral-950 dark:text-white">{t('login.title')}</h1>
        </div>

        <div className="motion-rise motion-delay-1 grid grid-cols-2 rounded-full bg-neutral-200/70 p-1 text-sm font-semibold dark:bg-neutral-900">
          <button
            className={`rounded-full px-3 py-2 transition ${
              mode === 'password'
                ? 'bg-white text-neutral-950 shadow-sm dark:bg-neutral-800 dark:text-white'
                : 'text-neutral-500 hover:text-neutral-950 dark:text-neutral-400 dark:hover:text-white'
            }`}
            type="button"
            onClick={() => setMode('password')}
          >
            {t('login.passwordMode')}
          </button>
          <button
            className={`rounded-full px-3 py-2 transition ${
              mode === 'code'
                ? 'bg-white text-neutral-950 shadow-sm dark:bg-neutral-800 dark:text-white'
                : 'text-neutral-500 hover:text-neutral-950 dark:text-neutral-400 dark:hover:text-white'
            }`}
            type="button"
            onClick={() => setMode('code')}
          >
            {t('login.codeMode')}
          </button>
        </div>

        <div className="motion-rise motion-delay-2 grid gap-4">
          <AuthField
            autoComplete="email"
            icon={<Mail className="size-4" />}
            label={t('auth.email')}
            name="email"
            placeholder="name@example.com"
            required
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          {mode === 'password' ? (
            <div className="grid gap-2">
              <AuthField
                autoComplete="current-password"
                icon={<LockKeyhole className="size-4" />}
                label={t('auth.password')}
                name="password"
                placeholder={t('auth.password')}
                required
                type="password"
              />
              <Link className="justify-self-end text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.resetPassword}>
                {t('auth.forgotPassword')}
              </Link>
            </div>
          ) : (
            <>
              {isCoolingDown ? (
                <CaptchaSentStatus
                  detail={formatCodeCooldownLabel(t('auth.resendIn'), remainingSeconds)}
                  title={t('auth.codeSentCompact')}
                />
              ) : (
                <HCaptchaBox
                  resetSignal={captchaResetSignal}
                  siteKey={env.hcaptchaSiteKey}
                  onChange={handleCaptchaChange}
                />
              )}
              <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
                <AuthField
                  autoComplete="one-time-code"
                  icon={<KeyRound className="size-4" />}
                  label={t('auth.code')}
                  name="code"
                  placeholder="000000"
                  required
                  type="text"
                />
                <Button
                  className="h-11"
                  disabled={isSendingCode || auth.loading || isCoolingDown}
                  type="button"
                  variant="secondary"
                  onClick={handleSendCode}
                >
                  {isSendingCode
                    ? t('auth.sending')
                    : isCoolingDown
                      ? formatCodeCooldownLabel(t('auth.resendIn'), remainingSeconds)
                      : t('auth.sendCode')}
                </Button>
              </div>
            </>
          )}
        </div>

        {errorMessage ? (
          <p className="motion-rise rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-300">
            {errorMessage}
          </p>
        ) : null}

        <Button className="motion-rise motion-delay-3 w-full" disabled={auth.loading} size="lg" type="submit">
          {auth.loading ? t('auth.loading') : t('auth.login')}
        </Button>

        <p className="motion-rise motion-delay-4 text-center text-sm text-neutral-500 dark:text-neutral-400">
          {t('login.switchText')}{' '}
          <Link className="font-semibold text-neutral-950 hover:text-[var(--color-accent-strong)] dark:text-white" state={{ returnTo }} to={routes.register}>
            {t('auth.register')}
          </Link>
        </p>
      </form>
    </AuthPageLayout>
  );
}
