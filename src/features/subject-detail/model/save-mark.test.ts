import { describe, expect, it, vi } from 'vitest';
import type { ParsedMarkDraft } from './mark-draft';
import { saveMarkChanges } from './save-mark';

const subjectId = '01980f00-0000-7000-8000-000000000001';
const draft: ParsedMarkDraft = {
  body: { status: 'done', simple_rating: 5, rating: '9.5', comment: 'Great', is_public: true },
  tagNames: ['favorite'],
  ratingDetails: [{ key: 'Music', value: '10' }],
};

function createOperations() {
  return {
    create: vi.fn(() => Promise.resolve()),
    update: vi.fn(() => Promise.resolve()),
    replaceTags: vi.fn(() => Promise.resolve()),
    replaceRatingDetails: vi.fn(() => Promise.resolve()),
    refresh: vi.fn(() => Promise.resolve()),
  };
}

describe('save mark changes', () => {
  it('creates the primary record before writing metadata and refreshing', async () => {
    const operations = createOperations();

    await saveMarkChanges({ subjectId, userSubjectId: null, draft }, operations);

    expect(operations.create).toHaveBeenCalledWith({ subject_id: subjectId, ...draft.body });
    expect(operations.update).not.toHaveBeenCalled();
    expect(operations.replaceTags).toHaveBeenCalledWith({ subjectId, tagNames: draft.tagNames });
    expect(operations.replaceRatingDetails).toHaveBeenCalledWith({ subjectId, details: draft.ratingDetails });
    expect(operations.refresh).toHaveBeenCalledOnce();
    expect(operations.create.mock.invocationCallOrder[0]).toBeLessThan(
      operations.replaceTags.mock.invocationCallOrder[0] ?? Number.POSITIVE_INFINITY,
    );
  });

  it('waits for every metadata write and refreshes before surfacing a partial failure', async () => {
    const operations = createOperations();
    const tagError = new Error('Tag update failed');
    let resolveDetails: (() => void) | undefined;
    operations.replaceTags.mockRejectedValue(tagError);
    operations.replaceRatingDetails.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveDetails = resolve;
      }),
    );

    const result = saveMarkChanges({ subjectId, userSubjectId: 42, draft }, operations);
    await vi.waitFor(() => {
      expect(operations.replaceRatingDetails).toHaveBeenCalledOnce();
    });
    expect(operations.refresh).not.toHaveBeenCalled();
    resolveDetails?.();

    await expect(result).rejects.toBe(tagError);
    expect(operations.update).toHaveBeenCalledWith({ userSubjectId: 42, body: draft.body });
    expect(operations.refresh).toHaveBeenCalledOnce();
  });

  it('refreshes after an ambiguous primary write failure without starting metadata writes', async () => {
    const operations = createOperations();
    const writeError = new Error('Connection closed');
    operations.create.mockRejectedValue(writeError);

    await expect(saveMarkChanges({ subjectId, userSubjectId: null, draft }, operations)).rejects.toBe(writeError);
    expect(operations.replaceTags).not.toHaveBeenCalled();
    expect(operations.replaceRatingDetails).not.toHaveBeenCalled();
    expect(operations.refresh).toHaveBeenCalledOnce();
  });
});
