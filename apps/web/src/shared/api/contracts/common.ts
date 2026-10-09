export type UUID = string;

export type ISODateString = string;

export type DateString = string;

export type DecimalString = string;

export type OpenString = string & Record<never, never>;

export type ApiPage<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type CursorPage<T> = {
  next: string | null;
  previous: string | null;
  results: T[];
};

export type PageQuery = {
  page?: number;
  page_size?: number;
};
