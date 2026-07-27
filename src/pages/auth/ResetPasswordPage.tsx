import { type FormEvent, useCallback, useState } from 'react';
import { Link, useNavigate } from '@/shared/routing/navigation';
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
import { Button } from '@/shared/ui/Button';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

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
  const handleCaptchaChange = useCallback((token: string) => setCaptchaToken(token), []);

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
      void navigate(auth.isAuthenticated ? routes.settings : routes.login, { replace: true });
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
          <img className="size-12 rounded-2xl" src="/brand/icon.svg" alt="" aria-hidden="true" />
          <h1 className="mt-5 text-2xl font-semibold tracking-tight text-neutral-950 dark:text-white">
            {t('auth.resetPassword')}
          </h1>
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
            placeholder={t('auth.password')}
            required
            type="password"
          />
          <AuthField
            autoComplete="new-password"
            icon={<LockKeyhole className="size-4" />}
            label={t('auth.confirmPassword')}
            name="confirm_password"
            placeholder={t('auth.password')}
            required
            type="password"
          />
        </div>

        {errorMessage ? (
          <p className="motion-rise rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-300">
            {errorMessage}
          </p>
        ) : null}

        <Button className="motion-rise motion-delay-2 w-full" disabled={isSubmitting} size="lg" type="submit">
          {isSubmitting ? t('auth.loading') : t('auth.resetPassword')}
        </Button>
        <p className="motion-rise motion-delay-3 text-center text-sm text-neutral-500 dark:text-neutral-400">
          <Link
            className="font-semibold text-neutral-950 hover:text-[var(--color-accent-strong)] dark:text-white"
            to={routes.login}
          >
            {t('auth.backToLogin')}
          </Link>
        </p>
      </form>
    </AuthPageLayout>
  );
}
