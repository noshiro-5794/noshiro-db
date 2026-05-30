export const routes = {
  home: '/',
  search: '/search',
  calendar: '/calendar',
  me: '/me',
  devApi: '/dev/api',
  subject: (subjectId: string) => `/subjects/${encodeURIComponent(subjectId)}`,
  subjectPattern: '/subjects/:subjectId',
} as const;
