import { useId, type ComponentProps, type ReactNode } from 'react';
import { Link } from '@tanstack/react-router';
import { ArrowLeft } from 'lucide-react';
import { publicAssetPaths } from '@/shared/assets/public-assets';
import { useI18n } from '@/shared/i18n';
import { Seo } from '@/shared/seo/Seo';
import { routes } from '@/shared/routing/paths';
import { Field, FieldLabel } from '@/shared/ui/Field';
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/shared/ui/InputGroup';

type AuthPageLayoutProps = {
  children: ReactNode;
  title: string;
};

type AuthFieldProps = ComponentProps<'input'> & {
  label: string;
  icon: ReactNode;
};

export function AuthPageLayout({ children, title }: AuthPageLayoutProps) {
  const { t } = useI18n();
  // Signed-out screens belong to the public surface and keep the light palette in every theme.
  return (
    <main className="flex min-h-screen flex-col bg-[var(--ui-bg-canvas)] text-[var(--ui-text)]" data-app-shell="public">
      <Seo noindex title={title} />
      {/*
       * These pages render outside the public shell, so they carry their own
       * minimal bar: without it a visitor who lands here has no way back.
       */}
      <header className="border-b border-[var(--ui-border-subtle)]">
        <div className="mx-auto flex h-14 w-full max-w-[1160px] items-center justify-between gap-4 px-4 sm:px-5">
          <Link className="flex items-center gap-2" aria-label="Noshiro DB" to={routes.home}>
            <img alt="" aria-hidden="true" className="size-6 rounded-[6px]" src={publicAssetPaths.appIcon} />
            <span className="text-[15px] font-semibold">Noshiro DB</span>
          </Link>
          <Link
            className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[var(--ui-text-muted)] transition-colors hover:text-[var(--ui-text)]"
            to={routes.home}
          >
            <ArrowLeft className="size-3.5" />
            {t('auth.backHome')}
          </Link>
        </div>
      </header>
      <div className="grid flex-1 place-items-center px-5 py-10">
        <div className="w-full max-w-[380px]">{children}</div>
      </div>
    </main>
  );
}

export function AuthField({ icon, label, className, ...props }: AuthFieldProps) {
  const generatedId = useId();
  const inputId = props.id ?? generatedId;

  return (
    <Field invalid={props['aria-invalid'] === true || props['aria-invalid'] === 'true'}>
      <FieldLabel htmlFor={inputId}>{label}</FieldLabel>
      <InputGroup size="lg">
        <InputGroupAddon aria-hidden="true">{icon}</InputGroupAddon>
        <InputGroupInput className={className} id={inputId} {...props} />
      </InputGroup>
    </Field>
  );
}
