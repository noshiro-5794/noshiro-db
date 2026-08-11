import { type SyntheticEvent, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from '@tanstack/react-router';
import { KeyRound, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { env } from '@/shared/config/env';
import { authApi } from '@/entities/session';
import { CaptchaSentStatus, HCaptchaBox } from '@/features/auth';
import { AuthField, AuthPageLayout } from '@/features/auth';
import { useAuth } from '@/entities/session';
import { formatCodeCooldownLabel, useCodeCooldown } from '@/features/auth';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { formDataString } from '@/shared/forms/form-data';
import { getErrorMessage } from '@/shared/lib/error';
import { returnTargetFromState } from '@/shared/routing/route-state';
import { Button } from '@/shared/ui/Button';

export function RegisterPage() {
  const { t } = useI18n();
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const returnTo =
    location.pathname === routes.register ? returnTargetFromState(location.state, routes.home) : location.href;
  const [email, setEmail] = useState('');
  const [captchaToken, setCaptchaToken] = useState('');
  const [captchaResetSignal, setCaptchaResetSignal] = useState(0);
  const [isSendingCode, setIsSendingCode] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const { isCoolingDown, remainingSeconds, startCooldown } = useCodeCooldown(60);
  const handleCaptchaChange = (token: string) => {
    setCaptchaToken(token);
    if (token) setErrorMessage('');
  };
  const handleCaptchaError = () => {
    setErrorMessage(t('auth.captchaUnavailable'));
  };

  useEffect(() => {
    if (!auth.isAuthenticated) return;

    void navigate({ href: returnTo, replace: true });
  }, [auth.isAuthenticated, navigate, returnTo]);

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
        purpose: 'register',
        ...(captchaToken ? { hcaptcha_token: captchaToken } : {}),
      });
      startCooldown();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, t('common.requestFailed')));
    } finally {
      if (env.hcaptchaSiteKey) {
        setCaptchaResetSignal((value) => value + 1);
        setCaptchaToken('');
      }
      setIsSendingCode(false);
    }
  }

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const input = {
      email: formDataString(formData, 'email').trim(),
      nickname: formDataString(formData, 'nickname').trim(),
      code: formDataString(formData, 'code').trim(),
      password: formDataString(formData, 'password'),
    };

    setErrorMessage('');
    try {
      await auth.register(input);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, t('common.requestFailed')));
    }
  }

  if (auth.isAuthenticated) return null;

  return (
    <AuthPageLayout title={t('register.title')}>
      <form className="grid gap-5" onSubmit={(event) => void handleSubmit(event)}>
        <div className="motion-rise grid justify-items-center text-center">
          <img className="size-12 rounded-lg" src="/brand/icon.svg" alt="" aria-hidden="true" />
          <h1 className="mt-5 text-2xl font-semibold tracking-normal text-[var(--ui-text)]">{t('register.title')}</h1>
        </div>

        <div className="motion-rise motion-delay-1 grid gap-4">
          <AuthField
            autoComplete="email"
            icon={<Mail className="size-4" />}
            label={t('auth.email')}
            name="email"
            maxLength={254}
            placeholder="name@example.com"
            required
            type="email"
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
            }}
          />
          <AuthField
            autoComplete="nickname"
            icon={<UserRound className="size-4" />}
            label={t('auth.nickname')}
            name="nickname"
            maxLength={32}
            minLength={2}
            placeholder={t('auth.displayName')}
            required
            type="text"
          />
          {isCoolingDown ? (
            <CaptchaSentStatus
              detail={formatCodeCooldownLabel(t('auth.resendIn'), remainingSeconds)}
              title={t('auth.codeSentCompact')}
            />
          ) : (
            <HCaptchaBox
              resetSignal={captchaResetSignal}
              retryLabel={t('common.retry')}
              siteKey={env.hcaptchaSiteKey}
              onChange={handleCaptchaChange}
              onError={handleCaptchaError}
            />
          )}
          <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
            <AuthField
              autoComplete="one-time-code"
              icon={<KeyRound className="size-4" />}
              label={t('auth.code')}
              name="code"
              inputMode="numeric"
              maxLength={6}
              minLength={6}
              pattern="[0-9]{6}"
              placeholder="000000"
              required
              type="text"
            />
            <Button
              className="h-11"
              disabled={isSendingCode || auth.loading || isCoolingDown}
              type="button"
              variant="secondary"
              onClick={() => void handleSendCode()}
            >
              {isSendingCode
                ? t('auth.sending')
                : isCoolingDown
                  ? formatCodeCooldownLabel(t('auth.resendIn'), remainingSeconds)
                  : t('auth.sendCode')}
            </Button>
          </div>
          <AuthField
            autoComplete="new-password"
            icon={<LockKeyhole className="size-4" />}
            label={t('auth.password')}
            name="password"
            minLength={8}
            placeholder={t('auth.password')}
            required
            type="password"
          />
        </div>

        {errorMessage ? (
          <p className="motion-rise rounded-lg bg-[var(--ui-danger-soft)] px-3 py-2 text-sm text-[var(--ui-danger-text)]">
            {errorMessage}
          </p>
        ) : null}

        <Button className="motion-rise motion-delay-2 w-full" disabled={auth.loading} size="lg" type="submit">
          {auth.loading ? t('auth.loading') : t('auth.register')}
        </Button>

        <p className="motion-rise motion-delay-3 text-center text-sm text-[var(--ui-text-muted)]">
          {t('register.switchText')}{' '}
          <Link
            className="font-semibold text-[var(--ui-text)] hover:text-[var(--ui-accent-text)]"
            state={{ returnTo }}
            to={routes.login}
          >
            {t('auth.login')}
          </Link>
        </p>
      </form>
    </AuthPageLayout>
  );
}
