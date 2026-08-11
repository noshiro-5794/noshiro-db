import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { Input } from './Input';
import { Field, FieldDescription, FieldError, FieldLabel } from './Field';

describe('Field accessibility contract', () => {
  it('associates Base UI inputs with labels and descriptions', () => {
    const markup = renderToStaticMarkup(
      <Field>
        <FieldLabel>Name</FieldLabel>
        <Input name="name" />
        <FieldDescription>Public display name</FieldDescription>
      </Field>,
    );

    const inputId = markup.match(/<input[^>]*id="([^"]+)"/)?.[1];

    expect(inputId).toBeTruthy();
    expect(markup).toContain(`for="${inputId}"`);
    expect(markup).toContain('Public display name');
  });

  it('exposes externally controlled errors through the field context', () => {
    const markup = renderToStaticMarkup(
      <Field invalid>
        <FieldLabel>Email</FieldLabel>
        <Input name="email" />
        <FieldError match>Email is invalid</FieldError>
      </Field>,
    );

    expect(markup).toContain('data-invalid');
    expect(markup).toContain('Email is invalid');
  });
});
