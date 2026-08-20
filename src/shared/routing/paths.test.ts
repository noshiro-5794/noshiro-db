import { describe, expect, it } from 'vitest';
import { routes } from './paths';

describe('route builders', () => {
  it('encodes path parameters', () => {
    expect(routes.entity('subject/id')).toBe('/entities/subject%2Fid');
    expect(routes.userCollection('42', 'collection id')).toBe('/users/42/collections/collection%20id');
  });

  it('encodes review query parameters', () => {
    expect(routes.reviewNewForSubject('subject&id')).toBe('/reviews/new?subjectId=subject%26id');
  });
});
