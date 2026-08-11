export type DateInput = string | number | Date | null | undefined;

function validDate(value: DateInput) {
  if (value === null || value === undefined || value === '') return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDateValue(value: DateInput, options: Intl.DateTimeFormatOptions, fallback = '') {
  const date = validDate(value);
  return date ? new Intl.DateTimeFormat(undefined, options).format(date) : fallback;
}

export function formatDate(value?: DateInput, fallback = '') {
  return formatDateValue(value, { dateStyle: 'medium' }, fallback);
}

export function formatDateTime(value?: DateInput, fallback = '') {
  return formatDateValue(value, { dateStyle: 'medium', timeStyle: 'short' }, fallback);
}

export function formatTime(value?: DateInput, fallback = '') {
  return formatDateValue(value, { timeStyle: 'short' }, fallback);
}
