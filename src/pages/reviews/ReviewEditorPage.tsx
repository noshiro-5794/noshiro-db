import { type SyntheticEvent, useEffect, useMemo, useState } from 'react';
import { getRouteApi, Link, useLocation } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, FileText, Lock, Save, ShieldAlert, Sparkles } from 'lucide-react';
import { libraryMutations, libraryQueries } from '@/entities/library';
import { useAuth } from '@/entities/session';
import { useI18n } from '@/shared/i18n';
import { invalidateReviewViews, MarkdownEditor } from '@/features/reviews';
import { subjectQueries } from '@/entities/subject';
import { routes } from '@/shared/routing/paths';
import { resolvedRouteHref } from '@/shared/routing/resolved-href';
import { parseIntegerParam } from '@/shared/routing/search-params';
import { parseUuid } from '@/shared/lib/validation';
import { backTargetFromState } from '@/shared/routing/route-state';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';
import { Toggle } from '@/shared/ui/Toggle';
import { toast } from '@/shared/ui/toast';

type ReviewRouteParams = {
  reviewId?: string;
};

type ReviewEditorPageProps = ReviewRouteParams & {
  onCreated: (reviewId: number, backTarget: string) => void;
  subjectIdParam?: string | undefined;
};

const newReviewRoute = getRouteApi('/reviews/new');
const editReviewRoute = getRouteApi('/reviews/$reviewId/edit');

function parseReviewId(value?: string) {
  if (!value || value === 'new') return null;
  return parseIntegerParam(value, { min: 1 });
}

function ReviewEditorPage({ onCreated, reviewId: reviewIdParam, subjectIdParam }: ReviewEditorPageProps) {
  const { t } = useI18n();
  const auth = useAuth();
  const location = useLocation();
  const queryClient = useQueryClient();
  const reviewId = parseReviewId(reviewIdParam);
  const subjectId = parseUuid(subjectIdParam) ?? '';
  const isEditing = reviewId !== null;

  const reviewQuery = useQuery({
    ...libraryQueries.review(reviewId ?? 0),
    enabled: isEditing,
  });
  const subjectQuery = useQuery({
    ...subjectQueries.detail(subjectId),
    enabled: !isEditing && Boolean(subjectId),
  });

  const [title, setTitle] = useState('');
  const [content, setContent] = useState(() => t('reviewEditor.starterMarkdown'));
  const [isPublic, setIsPublic] = useState(true);
  const [isSpoiler, setIsSpoiler] = useState(false);

  const subject = reviewQuery.data?.subject ?? subjectQuery.data;
  const subjectTitle = subject?.display_title || subject?.title || t('common.untitledSubject');
  const canCreate = !isEditing && Boolean(subjectId);
  const fallbackBackTarget = subject?.id ? routes.subject(subject.id) : routes.reviews;
  const backTarget = backTargetFromState(location, fallbackBackTarget);

  const createReviewMutation = useMutation({
    ...libraryMutations.createReview(),
    onError: () => toast.error(t('common.requestFailed')),
    onSuccess: async (review) => {
      await invalidateReviewViews(queryClient, { userId: auth.profile?.user_id });
      toast.success(t('reviewEditor.created'));
      onCreated(review.id, backTarget);
    },
  });
  const updateReviewMutation = useMutation({
    ...libraryMutations.updateReview(),
    onError: () => toast.error(t('common.requestFailed')),
    onSuccess: async () => {
      await invalidateReviewViews(queryClient, { userId: auth.profile?.user_id });
      toast.success(t('reviewEditor.saved'));
    },
  });
  const isSaving = createReviewMutation.isPending || updateReviewMutation.isPending;
  const hasTarget = isEditing || canCreate;

  const titlePlaceholder = useMemo(() => {
    if (!subject) return t('reviewEditor.titlePlaceholder');
    return `${t('reviewEditor.titleForSubject')}: ${subjectTitle}`;
  }, [subject, subjectTitle, t]);

  useEffect(() => {
    if (!reviewQuery.data) return;
    setTitle(reviewQuery.data.title);
    setContent(reviewQuery.data.content || '');
    setIsPublic(reviewQuery.data.is_public);
    setIsSpoiler(reviewQuery.data.is_spoiler);
  }, [reviewQuery.data]);

  function handleSubmit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    const payload = {
      title: (title.trim() || titlePlaceholder).slice(0, 256),
      content,
      is_public: isPublic,
      is_spoiler: isSpoiler,
    };

    if (isEditing && reviewId) {
      updateReviewMutation.mutate({ reviewId, body: payload });
      return;
    }
    if (canCreate) {
      createReviewMutation.mutate({ subjectId, body: payload });
    }
  }

  if (isEditing && reviewQuery.isLoading) {
    return (
      <Page title={t('reviewEditor.title')} eyebrow={t('nav.groupLibrary')}>
        <LoadingState title={t('reviewEditor.loading')} />
      </Page>
    );
  }

  if ((isEditing && reviewQuery.isError) || (!isEditing && subjectQuery.isError)) {
    return (
      <Page title={t('reviewEditor.title')} eyebrow={t('nav.groupLibrary')}>
        <ErrorState title={t('reviewEditor.errorTitle')} description={t('reviewEditor.errorBody')} />
      </Page>
    );
  }

  return (
    <Page
      actions={
        <>
          <Button asChild variant="ghost">
            <Link {...resolvedRouteHref(backTarget)}>
              <ArrowLeft className="size-4" /> {t('common.back')}
            </Link>
          </Button>
          <Button disabled={!hasTarget || isSaving} form="review-editor-form" type="submit">
            <Save className="size-4" /> {isSaving ? t('common.saving') : t('common.save')}
          </Button>
        </>
      }
      description={subject ? subjectTitle : undefined}
      eyebrow={t('nav.groupLibrary')}
      title={isEditing ? t('reviewEditor.editTitle') : t('reviewEditor.newTitle')}
    >
      {!hasTarget ? (
        <ErrorState title={t('reviewEditor.noSubjectTitle')} description={t('reviewEditor.noSubjectBody')} />
      ) : (
        <form className="review-editor-page" id="review-editor-form" onSubmit={handleSubmit}>
          <section className="review-editor-document">
            <div className="min-w-0">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <Badge variant="accent">
                  <Sparkles className="size-3" /> {t('common.markdown')}
                </Badge>
                <Badge variant="secondary">
                  <FileText className="size-3" /> {t('common.review')}
                </Badge>
                <Badge variant={isPublic ? 'accent' : 'secondary'}>
                  {isPublic ? t('common.public') : t('common.private')}
                </Badge>
                {isSpoiler ? (
                  <Badge>
                    <ShieldAlert className="size-3" /> {t('common.spoiler')}
                  </Badge>
                ) : null}
              </div>
              <Input
                aria-label={t('reviewEditor.titlePlaceholder')}
                className="h-12 rounded-none border-0 bg-transparent px-0 text-xl font-semibold shadow-none ring-0 hover:border-transparent focus:border-transparent focus:ring-0"
                maxLength={256}
                placeholder={titlePlaceholder}
                value={title}
                onChange={(event) => {
                  setTitle(event.target.value);
                }}
              />
            </div>
            <div className="review-editor-flags">
              <Toggle pressed={isPublic} onPressedChange={setIsPublic}>
                <Lock className="size-4" />
                {isPublic ? t('common.public') : t('common.private')}
              </Toggle>
              <Toggle pressed={isSpoiler} onPressedChange={setIsSpoiler}>
                <ShieldAlert className="size-4" />
                {t('common.spoiler')}
              </Toggle>
            </div>
          </section>

          <MarkdownEditor maxLength={20_000} value={content} onChange={setContent} />
        </form>
      )}
    </Page>
  );
}

export function NewReviewPage() {
  const { subjectId } = newReviewRoute.useSearch();
  const navigate = newReviewRoute.useNavigate();

  return (
    <ReviewEditorPage
      subjectIdParam={subjectId}
      onCreated={(reviewId, backTarget) =>
        void navigate({
          params: { reviewId: String(reviewId) },
          replace: true,
          state: { from: backTarget },
          to: '/reviews/$reviewId/edit',
        })
      }
    />
  );
}

export function EditReviewPage() {
  const { reviewId } = editReviewRoute.useParams();
  const navigate = editReviewRoute.useNavigate();

  return (
    <ReviewEditorPage
      reviewId={reviewId}
      onCreated={(createdReviewId, backTarget) =>
        void navigate({
          params: { reviewId: String(createdReviewId) },
          replace: true,
          state: { from: backTarget },
          to: '/reviews/$reviewId/edit',
        })
      }
    />
  );
}
