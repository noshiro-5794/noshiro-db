import { type FormEvent, useCallback, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { KeyRound, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { env } from '@/config/env';
import { authApi } from '@/features/auth/api';
import { HCaptchaBox } from '@/features/auth/components/HCaptchaBox';
import { AuthField, AuthPageLayout } from '@/features/auth/components/AuthPageLayout';
import { useAuth } from '@/features/auth/use-auth';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';
import { Button } from '@/shared/ui/Button';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function RegisterPage() {
  const { t } = useI18n();
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const returnTo = typeof location.state?.returnTo === 'string' && location.state.returnTo.startsWith('/') ? location.state.returnTo : routes.home;
  const [email, setEmail] = useState('');
  const [captchaToken, setCaptchaToken] = useState('');
  const [captchaResetSignal, setCaptchaResetSignal] = useState(0);
  const [isSendingCode, setIsSendingCode] = useState(false);
  const [noticeMessage, setNoticeMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
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
    setNoticeMessage('');
    try {
      await authApi.sendCode({
        email: trimmedEmail,
        purpose: 'register',
        hcaptcha_token: captchaToken || undefined,
      });
      setNoticeMessage(t('auth.codeSent'));
      setCaptchaResetSignal((value) => value + 1);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, t('common.requestFailed')));
    } finally {
      setIsSendingCode(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const input = {
      email: String(formData.get('email') ?? '').trim(),
      nickname: String(formData.get('nickname') ?? '').trim(),
      code: String(formData.get('code') ?? '').trim(),
      password: String(formData.get('password') ?? ''),
    };

    setErrorMessage('');
    try {
      await auth.register(input);
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
          <h1 className="mt-5 text-2xl font-semibold tracking-tight text-neutral-950 dark:text-white">{t('register.title')}</h1>
        </div>

        <div className="motion-rise motion-delay-1 grid gap-4">
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
          <AuthField
            autoComplete="nickname"
            icon={<UserRound className="size-4" />}
            label={t('auth.nickname')}
            name="nickname"
            placeholder={t('auth.displayName')}
            required
            type="text"
          />
          <HCaptchaBox
            resetSignal={captchaResetSignal}
            siteKey={env.hcaptchaSiteKey}
            onChange={handleCaptchaChange}
          />
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
              disabled={isSendingCode || auth.loading}
              type="button"
              variant="secondary"
              onClick={handleSendCode}
            >
              {isSendingCode ? t('auth.sending') : t('auth.sendCode')}
            </Button>
          </div>
          <AuthField
            autoComplete="new-password"
            icon={<LockKeyhole className="size-4" />}
            label={t('auth.password')}
            name="password"
            placeholder={t('auth.password')}
            required
            type="password"
          />
        </div>

        {noticeMessage ? (
          <p className="motion-rise rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
            {noticeMessage}
          </p>
        ) : null}
        {errorMessage ? (
          <p className="motion-rise rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-300">
            {errorMessage}
          </p>
        ) : null}

        <Button className="motion-rise motion-delay-2 w-full" disabled={auth.loading} size="lg" type="submit">
          {auth.loading ? t('auth.loading') : t('auth.register')}
        </Button>

        <p className="motion-rise motion-delay-3 text-center text-sm text-neutral-500 dark:text-neutral-400">
          {t('register.switchText')}{' '}
          <Link className="font-semibold text-neutral-950 hover:text-[var(--color-accent-strong)] dark:text-white" state={{ returnTo }} to={routes.login}>
            {t('auth.login')}
          </Link>
        </p>
      </form>
    </AuthPageLayout>
  );
}
