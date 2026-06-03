import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, FileText, Lock, Save, ShieldAlert, Sparkles } from 'lucide-react';
import { libraryMutations, libraryQueries, libraryQueryKeys } from '@/features/library/library-queries';
import { useI18n } from '@/features/i18n/use-i18n';
import { MarkdownEditor } from '@/features/reviews/components/MarkdownEditor';
import { subjectQueries } from '@/features/subjects/subject-queries';
import { routes } from '@/routes/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';
import { toast } from 'sonner';

type ReviewRouteParams = {
  reviewId?: string;
};

function parseReviewId(value?: string) {
  if (!value || value === 'new') return null;
  const reviewId = Number(value);
  return Number.isInteger(reviewId) && reviewId > 0 ? reviewId : null;
}

export function ReviewEditorPage() {
  const { t } = useI18n();
  const { reviewId: reviewIdParam } = useParams<ReviewRouteParams>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const reviewId = parseReviewId(reviewIdParam);
  const subjectId = searchParams.get('subjectId') ?? '';
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
  const backTarget = subject?.id ? routes.subject(subject.id) : routes.reviews;

  const createReviewMutation = useMutation({
    ...libraryMutations.createReview(),
    onSuccess: async (review) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: libraryQueryKeys.reviews() }),
        subject?.id ? queryClient.invalidateQueries({ queryKey: libraryQueryKeys.subjectReviews(subject.id) }) : Promise.resolve(),
      ]);
      toast.success(t('reviewEditor.created'));
      navigate(routes.reviewEdit(review.id));
    },
  });
  const updateReviewMutation = useMutation({
    ...libraryMutations.updateReview(),
    onSuccess: async (review) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: libraryQueryKeys.reviews() }),
        queryClient.invalidateQueries({ queryKey: libraryQueryKeys.reviewDetail(review.id) }),
        review.subject?.id ? queryClient.invalidateQueries({ queryKey: libraryQueryKeys.subjectReviews(review.subject.id) }) : Promise.resolve(),
      ]);
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

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = {
      title: title.trim() || titlePlaceholder,
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
    return <Page title={t('reviewEditor.title')} eyebrow={t('reviews.title')}><LoadingState title={t('reviewEditor.loading')} /></Page>;
  }

  if ((isEditing && reviewQuery.isError) || (!isEditing && subjectQuery.isError)) {
    return <Page title={t('reviewEditor.title')} eyebrow={t('reviews.title')}><ErrorState title={t('reviewEditor.errorTitle')} description={t('reviewEditor.errorBody')} /></Page>;
  }

  return (
    <Page
      actions={(
        <>
          <Button asChild variant="ghost">
            <Link to={backTarget}><ArrowLeft className="size-4" /> {t('common.back')}</Link>
          </Button>
          <Button disabled={!hasTarget || isSaving} form="review-editor-form" type="submit">
            <Save className="size-4" /> {isSaving ? t('common.saving') : t('common.save')}
          </Button>
        </>
      )}
      description={subject ? subjectTitle : t('reviewEditor.description')}
      eyebrow={t('reviews.title')}
      title={isEditing ? t('reviewEditor.editTitle') : t('reviewEditor.newTitle')}
    >
      {!hasTarget ? (
        <ErrorState title={t('reviewEditor.noSubjectTitle')} description={t('reviewEditor.noSubjectBody')} />
      ) : (
        <form className="review-editor-page" id="review-editor-form" onSubmit={handleSubmit}>
          <section className="review-editor-document">
            <div className="min-w-0">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <Badge variant="accent"><Sparkles className="size-3" /> {t('common.markdown')}</Badge>
                <Badge variant="secondary"><FileText className="size-3" /> {t('common.review')}</Badge>
                <Badge variant={isPublic ? 'accent' : 'secondary'}>{isPublic ? t('common.public') : t('common.private')}</Badge>
                {isSpoiler ? <Badge><ShieldAlert className="size-3" /> {t('common.spoiler')}</Badge> : null}
              </div>
              <Input
                className="h-12 rounded-none bg-transparent px-0 text-xl font-semibold shadow-none ring-0 focus:ring-0"
                placeholder={titlePlaceholder}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
            </div>
            <div className="review-editor-flags">
              <button className={isPublic ? 'is-active' : ''} type="button" onClick={() => setIsPublic((value) => !value)}>
                <Lock className="size-4" />
                {isPublic ? t('common.public') : t('common.private')}
              </button>
              <button className={isSpoiler ? 'is-active' : ''} type="button" onClick={() => setIsSpoiler((value) => !value)}>
                <ShieldAlert className="size-4" />
                {t('common.spoiler')}
              </button>
            </div>
          </section>

          <MarkdownEditor value={content} onChange={setContent} />
        </form>
      )}
    </Page>
  );
}
