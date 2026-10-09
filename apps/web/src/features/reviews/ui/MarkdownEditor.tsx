import { type ChangeEvent, useMemo, useRef, useState } from 'react';
import {
  Bold,
  Code2,
  Eye,
  Heading1,
  Heading2,
  Italic,
  Link2,
  List,
  ListOrdered,
  PanelLeftClose,
  PanelRightClose,
  PencilLine,
  Quote,
  Split,
  Table2,
} from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { Textarea } from '@/shared/ui/Textarea';
import { MarkdownRenderer } from './MarkdownRenderer';
import './review-editor.css';

type MarkdownEditorProps = {
  maxLength?: number;
  value: string;
  onChange: (value: string) => void;
};

type EditorMode = 'split' | 'write' | 'preview';

function countWords(value: string) {
  const latinWords = value.trim().match(/[A-Za-z0-9_]+/g)?.length ?? 0;
  const cjkChars = value.match(/[\u3040-\u30ff\u3400-\u9fff]/g)?.length ?? 0;
  return latinWords + cjkChars;
}

function insertMarkdown(current: string, selectionStart: number, selectionEnd: number, prefix: string, suffix: string) {
  const selected = current.slice(selectionStart, selectionEnd);
  const before = current.slice(0, selectionStart);
  const after = current.slice(selectionEnd);
  return `${before}${prefix}${selected}${suffix}${after}`;
}

function getOutline(value: string) {
  return value
    .split('\n')
    .map((line, index) => {
      const match = /^(#{1,3})\s+(.+)$/.exec(line.trim());
      const depthMarker = match?.[1];
      const title = match?.[2];
      return depthMarker && title ? { depth: depthMarker.length, title, line: index + 1 } : null;
    })
    .filter((item): item is { depth: number; title: string; line: number } => Boolean(item))
    .slice(0, 12);
}

export function MarkdownEditor({ maxLength, value, onChange }: MarkdownEditorProps) {
  const { t } = useI18n();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [mode, setMode] = useState<EditorMode>('split');
  const toolbarGroups = [
    [
      { label: t('reviewEditor.bold'), icon: Bold, prefix: '**', suffix: '**' },
      { label: t('reviewEditor.italic'), icon: Italic, prefix: '*', suffix: '*' },
      { label: t('reviewEditor.inlineCode'), icon: Code2, prefix: '`', suffix: '`' },
      { label: t('reviewEditor.link'), icon: Link2, prefix: '[', suffix: '](https://)' },
    ],
    [
      { label: 'H1', icon: Heading1, prefix: '# ', suffix: '' },
      { label: 'H2', icon: Heading2, prefix: '## ', suffix: '' },
      { label: t('reviewEditor.quote'), icon: Quote, prefix: '> ', suffix: '' },
    ],
    [
      { label: t('reviewEditor.list'), icon: List, prefix: '- ', suffix: '' },
      { label: t('reviewEditor.numberedList'), icon: ListOrdered, prefix: '1. ', suffix: '' },
      {
        label: t('reviewEditor.table'),
        icon: Table2,
        prefix: '\n| Key | Value |\n| --- | --- |\n|  |  |\n',
        suffix: '',
      },
    ],
  ];
  const stats = useMemo(
    () => ({
      words: countWords(value),
      chars: value.length,
      minutes: Math.max(1, Math.ceil(countWords(value) / 260)),
    }),
    [value],
  );
  const outline = useMemo(() => getOutline(value), [value]);

  function handleToolbarClick(prefix: string, suffix: string) {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const { selectionEnd, selectionStart } = textarea;
    const insertedValue = insertMarkdown(value, selectionStart, selectionEnd, prefix, suffix);
    const nextValue = maxLength ? insertedValue.slice(0, maxLength) : insertedValue;
    onChange(nextValue);
    requestAnimationFrame(() => {
      textarea.focus();
      const nextSelectionStart = selectionStart + prefix.length;
      const nextSelectionEnd = selectionEnd + prefix.length;
      textarea.setSelectionRange(nextSelectionStart, nextSelectionEnd);
    });
  }

  function handleChange(event: ChangeEvent<HTMLTextAreaElement>) {
    onChange(event.target.value);
  }

  function focusLine(lineNumber: number) {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const offset = value
      .split('\n')
      .slice(0, lineNumber - 1)
      .join('\n').length;
    const cursor = lineNumber > 1 ? offset + 1 : 0;
    textarea.focus();
    textarea.setSelectionRange(cursor, cursor);
  }

  return (
    <section className="review-workbench">
      <div className="review-editor">
        <header className="review-editor-toolbar">
          <div className="review-editor-toolgroups">
            {toolbarGroups.map((group, groupIndex) => (
              <div className="review-editor-toolgroup" key={groupIndex}>
                {group.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Button
                      aria-label={item.label}
                      key={item.label}
                      size="icon"
                      tooltip={item.label}
                      type="button"
                      variant="ghost"
                      onClick={() => {
                        handleToolbarClick(item.prefix, item.suffix);
                      }}
                    >
                      <Icon className="size-4" />
                    </Button>
                  );
                })}
              </div>
            ))}
          </div>
          <div className="review-editor-actions">
            <div className="review-editor-status">
              <span>
                {stats.words} {t('common.words')}
              </span>
              <span>
                {stats.minutes} {t('common.min')}
              </span>
            </div>
            <div className="review-editor-mode">
              <Button
                aria-label={t('reviewEditor.write')}
                aria-pressed={mode === 'write'}
                size="icon"
                tooltip={t('reviewEditor.write')}
                type="button"
                variant={mode === 'write' ? 'secondary' : 'ghost'}
                onClick={() => {
                  setMode('write');
                }}
              >
                <PanelLeftClose className="size-4" />
              </Button>
              <Button
                aria-label={t('reviewEditor.split')}
                aria-pressed={mode === 'split'}
                size="icon"
                tooltip={t('reviewEditor.split')}
                type="button"
                variant={mode === 'split' ? 'secondary' : 'ghost'}
                onClick={() => {
                  setMode('split');
                }}
              >
                <Split className="size-4" />
              </Button>
              <Button
                aria-label={t('reviewEditor.preview')}
                aria-pressed={mode === 'preview'}
                size="icon"
                tooltip={t('reviewEditor.preview')}
                type="button"
                variant={mode === 'preview' ? 'secondary' : 'ghost'}
                onClick={() => {
                  setMode('preview');
                }}
              >
                <PanelRightClose className="size-4" />
              </Button>
            </div>
          </div>
        </header>

        {outline.length ? (
          <nav aria-label={t('reviewEditor.outline')} className="review-editor-outlinebar">
            <span>{t('reviewEditor.outline')}</span>
            <div>
              {outline.map((item) => (
                <Button
                  data-depth={item.depth}
                  key={`${item.line}-${item.title}`}
                  variant="unstyled"
                  onClick={() => {
                    focusLine(item.line);
                  }}
                >
                  {item.title}
                </Button>
              ))}
            </div>
          </nav>
        ) : null}

        <div className={`review-editor-grid is-${mode}`}>
          <div className="review-editor-pane review-editor-write">
            <div className="review-editor-pane-header">
              <span>
                <PencilLine className="size-4" /> {t('common.markdown')}
              </span>
              <span>
                {stats.words} {t('common.words')}
              </span>
            </div>
            <Textarea
              aria-label={t('reviewEditor.title')}
              className="review-editor-textarea"
              maxLength={maxLength}
              ref={textareaRef}
              placeholder={t('reviewEditor.placeholder')}
              spellCheck
              value={value}
              onChange={handleChange}
            />
          </div>

          <div className="review-editor-pane review-editor-preview">
            <div className="review-editor-pane-header">
              <span>
                <Eye className="size-4" /> {t('reviewEditor.preview')}
              </span>
              <span>
                {stats.minutes} {t('common.minRead')}
              </span>
            </div>
            <div className="review-editor-preview-body">
              {value.trim() ? (
                <MarkdownRenderer content={value} />
              ) : (
                <p className="text-sm text-[var(--ui-text-muted)]">{t('reviewEditor.previewEmpty')}</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
