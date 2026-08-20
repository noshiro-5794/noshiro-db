import type { UUID } from '@/shared/api';
import type { ParsedMarkDraft } from './mark-draft';

type SaveMarkInput = {
  subjectId: UUID;
  userSubjectId: number | null;
  draft: ParsedMarkDraft;
};

type SaveMarkOperations = {
  create: (body: ParsedMarkDraft['body'] & { entity_id: UUID }) => Promise<unknown>;
  update: (input: { userSubjectId: number; body: ParsedMarkDraft['body'] }) => Promise<unknown>;
  replaceTags: (input: { subjectId: UUID; tagNames: string[] }) => Promise<unknown>;
  replaceRatingDetails: (input: { subjectId: UUID; details: ParsedMarkDraft['ratingDetails'] }) => Promise<unknown>;
  refresh: () => Promise<unknown>;
};

type OperationResult = { ok: true } | { ok: false; error: unknown };

async function captureOperation(operation: () => Promise<void>): Promise<OperationResult> {
  try {
    await operation();
    return { ok: true };
  } catch (error) {
    return { ok: false, error };
  }
}

export async function saveMarkChanges(input: SaveMarkInput, operations: SaveMarkOperations) {
  const writeResult = await captureOperation(async () => {
    if (input.userSubjectId === null) {
      await operations.create({ entity_id: input.subjectId, ...input.draft.body });
    } else {
      await operations.update({ userSubjectId: input.userSubjectId, body: input.draft.body });
    }

    const metadataResults = await Promise.allSettled([
      operations.replaceTags({ subjectId: input.subjectId, tagNames: input.draft.tagNames }),
      operations.replaceRatingDetails({ subjectId: input.subjectId, details: input.draft.ratingDetails }),
    ]);
    const failedMetadataWrite = metadataResults.find(
      (result): result is PromiseRejectedResult => result.status === 'rejected',
    );
    if (failedMetadataWrite) throw failedMetadataWrite.reason;
  });

  const refreshResult = await captureOperation(async () => {
    await operations.refresh();
  });

  if (!writeResult.ok) throw writeResult.error;
  if (!refreshResult.ok) throw refreshResult.error;
}
