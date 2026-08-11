import { useId, type ComponentProps, type ReactNode } from 'react';
import { Seo } from '@/shared/seo/Seo';
import { Field, FieldLabel } from '@/shared/ui/Field';
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/shared/ui/InputGroup';
import '@/shared/ui/motion.css';

type AuthPageLayoutProps = {
  children: ReactNode;
  title: string;
};

type AuthFieldProps = ComponentProps<'input'> & {
  label: string;
  icon: ReactNode;
};

export function AuthPageLayout({ children, title }: AuthPageLayoutProps) {
  return (
    <main className="grid min-h-screen place-items-center bg-[var(--ui-bg-canvas)] px-5 py-10 text-[var(--ui-text)]">
      <Seo noindex title={title} />
      <div className="w-full max-w-[380px]">{children}</div>
    </main>
  );
}

export function AuthField({ icon, label, className, ...props }: AuthFieldProps) {
  const generatedId = useId();
  const inputId = props.id ?? generatedId;

  return (
    <Field invalid={props['aria-invalid'] === true || props['aria-invalid'] === 'true'}>
      <FieldLabel htmlFor={inputId}>{label}</FieldLabel>
      <InputGroup>
        <InputGroupAddon aria-hidden="true">{icon}</InputGroupAddon>
        <InputGroupInput className={className} id={inputId} {...props} />
      </InputGroup>
    </Field>
  );
}
