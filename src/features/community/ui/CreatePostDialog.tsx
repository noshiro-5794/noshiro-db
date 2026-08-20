import { type SyntheticEvent, useId, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { MessageSquare } from 'lucide-react';
import { communityMutations } from '@/entities/community';
import { useI18n } from '@/shared/i18n';
import { parseUuid } from '@/shared/lib/validation';
import { Button } from '@/shared/ui/Button';
import { CheckboxField } from '@/shared/ui/Checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/shared/ui/Dialog';
import { Field, FieldLabel } from '@/shared/ui/Field';
import { Input } from '@/shared/ui/Input';
import { Textarea } from '@/shared/ui/Textarea';
import { toast } from '@/shared/ui/toast';
import { Toggle, ToggleGroup } from '@/shared/ui/Toggle';
import { invalidateCommunityTargets } from '../model/cache';

export function CreatePostDialog() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [visibility, setVisibility] = useState<'public' | 'followers' | 'private'>('public');
  const [isSpoiler, setIsSpoiler] = useState(false);
  const [isNsfw, setIsNsfw] = useState(false);
  const contentId = useId();
  const subjectIdInputId = useId();
  const visibilityLegendId = useId();

  const createPostMutation = useMutation({
    ...communityMutations.createPost(),
    onError: () => toast.error(t('common.requestFailed')),
    onSuccess: async () => {
      setOpen(false);
      setContent('');
      setSubjectId('');
      setVisibility('public');
      setIsSpoiler(false);
      setIsNsfw(false);
      await invalidateCommunityTargets(queryClient);
    },
  });

  function submitPost(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    const normalizedContent = content.trim();
    if (!normalizedContent) return;
    const normalizedSubjectId = subjectId.trim() ? parseUuid(subjectId.trim()) : null;
    if (subjectId.trim() && !normalizedSubjectId) {
      toast.error(t('community.invalidSubjectId'));
      return;
    }
    createPostMutation.mutate({
      content: normalizedContent,
      ...(normalizedSubjectId ? { entity_id: normalizedSubjectId } : {}),
      visibility,
      is_spoiler: isSpoiler,
      is_nsfw: isNsfw,
    });
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button type="button" />}>
        <MessageSquare aria-hidden="true" className="size-4" /> {t('community.newPost')}
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t('community.createPostTitle')}</DialogTitle>
          <DialogDescription>{t('community.createPostDescription')}</DialogDescription>
        </DialogHeader>
        <form aria-busy={createPostMutation.isPending} className="grid gap-4" onSubmit={submitPost}>
          <Field>
            <FieldLabel className="sr-only" htmlFor={contentId}>
              {t('community.postPlaceholder')}
            </FieldLabel>
            <Textarea
              required
              className="min-h-36"
              id={contentId}
              maxLength={10_000}
              name="content"
              value={content}
              placeholder={t('community.postPlaceholder')}
              onChange={(event) => {
                setContent(event.target.value);
              }}
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field>
              <FieldLabel htmlFor={subjectIdInputId}>{t('community.attachSubjectId')}</FieldLabel>
              <Input
                id={subjectIdInputId}
                maxLength={36}
                name="subjectId"
                value={subjectId}
                placeholder="00000000-0000-0000-0000-000000000000"
                onChange={(event) => {
                  setSubjectId(event.target.value);
                }}
              />
            </Field>
            <fieldset className="m-0 grid min-w-0 gap-2 border-0 p-0">
              <legend className="text-[13px] font-medium leading-5 text-foreground" id={visibilityLegendId}>
                {t('community.visibility')}
              </legend>
              <ToggleGroup
                aria-labelledby={visibilityLegendId}
                className="grid min-w-0 grid-cols-3"
                value={[visibility]}
                onValueChange={(values) => {
                  const nextVisibility = values[0];
                  if (nextVisibility) setVisibility(nextVisibility);
                }}
              >
                {(
                  [
                    ['public', t('common.public')],
                    ['followers', t('community.followersVisibility')],
                    ['private', t('common.private')],
                  ] as const
                ).map(([value, label]) => (
                  <Toggle className="min-w-0 w-full px-1 text-xs" key={value} value={value}>
                    {label}
                  </Toggle>
                ))}
              </ToggleGroup>
            </fieldset>
          </div>
          <div className="flex flex-wrap gap-3 text-sm text-[var(--ui-text-muted)]">
            <CheckboxField checked={isSpoiler} onCheckedChange={setIsSpoiler}>
              {t('community.markSpoiler')}
            </CheckboxField>
            <CheckboxField checked={isNsfw} onCheckedChange={setIsNsfw}>
              NSFW
            </CheckboxField>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setOpen(false);
              }}
            >
              {t('common.cancel')}
            </Button>
            <Button disabled={createPostMutation.isPending || !content.trim()} type="submit">
              <MessageSquare aria-hidden="true" className="size-4" /> {t('community.publishPost')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
