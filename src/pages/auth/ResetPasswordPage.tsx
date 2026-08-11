import { type SyntheticEvent, useCallback, useState } from 'react';
import { Link, useNavigate } from '@tanstack/react-router';
import { KeyRound, LockKeyhole, Mail } from 'lucide-react';
import { env } from '@/shared/config/env';
import { authApi } from '@/entities/session';
import { AuthField, AuthPageLayout } from '@/features/auth';
import { CaptchaSentStatus, HCaptchaBox } from '@/features/auth';
import { useAuth } from '@/entities/session';
import { formatCodeCooldownLabel, useCodeCooldown } from '@/features/auth';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { formDataString } from '@/shared/forms/form-data';
import { getErrorMessage } from '@/shared/lib/error';
import { Button } from '@/shared/ui/Button';

export function ResetPasswordPage() {
  const { t } = useI18n();
  const auth = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState(auth.profile?.email ?? '');
  const [captchaToken, setCaptchaToken] = useState('');
  const [captchaResetSignal, setCaptchaResetSignal] = useState(0);
  const [isSendingCode, setIsSendingCode] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const { isCoolingDown, remainingSeconds, startCooldown } = useCodeCooldown(60);
  const handleCaptchaChange = useCallback((token: string) => {
    setCaptchaToken(token);
    if (token) setErrorMessage('');
  }, []);
  const handleCaptchaError = useCallback(() => {
    setErrorMessage(t('auth.captchaUnavailable'));
  }, [t]);

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
        purpose: 'reset_password',
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
    const nextPassword = formDataString(formData, 'new_password');
    const confirmPassword = formDataString(formData, 'confirm_password');
    if (nextPassword !== confirmPassword) {
      setErrorMessage(t('auth.passwordMismatch'));
      return;
    }

    setIsSubmitting(true);
    setErrorMessage('');
    try {
      await authApi.resetPassword({
        email: formDataString(formData, 'email').trim(),
        code: formDataString(formData, 'code').trim(),
        new_password: nextPassword,
      });
      void navigate({ replace: true, to: auth.isAuthenticated ? '/settings' : '/login' });
    } catch (error) {
      setErrorMessage(getErrorMessage(error, t('common.requestFailed')));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthPageLayout title={t('auth.resetPassword')}>
      <form className="grid gap-5" onSubmit={(event) => void handleSubmit(event)}>
        <div className="motion-rise grid justify-items-center text-center">
          <img className="size-12 rounded-lg" src="/brand/icon.svg" alt="" aria-hidden="true" />
          <h1 className="mt-5 text-2xl font-semibold tracking-normal text-[var(--ui-text)]">
            {t('auth.resetPassword')}
          </h1>
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
              disabled={isSendingCode || isSubmitting || isCoolingDown}
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
            label={t('auth.newPassword')}
            name="new_password"
            minLength={8}
            placeholder={t('auth.password')}
            required
            type="password"
          />
          <AuthField
            autoComplete="new-password"
            icon={<LockKeyhole className="size-4" />}
            label={t('auth.confirmPassword')}
            name="confirm_password"
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

        <Button className="motion-rise motion-delay-2 w-full" disabled={isSubmitting} size="lg" type="submit">
          {isSubmitting ? t('auth.loading') : t('auth.resetPassword')}
        </Button>
        <p className="motion-rise motion-delay-3 text-center text-sm text-[var(--ui-text-muted)]">
          <Link className="font-semibold text-[var(--ui-text)] hover:text-[var(--ui-accent-text)]" to={routes.login}>
            {t('auth.backToLogin')}
          </Link>
        </p>
      </form>
    </AuthPageLayout>
  );
}
