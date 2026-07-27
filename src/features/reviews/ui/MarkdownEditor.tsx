import { type ChangeEvent, useMemo, useState } from 'react';
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
import { MarkdownRenderer } from './MarkdownRenderer';

type MarkdownEditorProps = {
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
      return match ? { depth: match[1].length, title: match[2], line: index + 1 } : null;
    })
    .filter((item): item is { depth: number; title: string; line: number } => Boolean(item))
    .slice(0, 12);
}

export function MarkdownEditor({ value, onChange }: MarkdownEditorProps) {
  const { t } = useI18n();
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
    const textarea = document.getElementById('review-markdown-editor') as HTMLTextAreaElement | null;
    if (!textarea) return;
    const nextValue = insertMarkdown(value, textarea.selectionStart, textarea.selectionEnd, prefix, suffix);
    onChange(nextValue);
    requestAnimationFrame(() => {
      textarea.focus();
      const cursor = textarea.selectionStart + prefix.length;
      textarea.setSelectionRange(cursor, cursor);
    });
  }

  function handleChange(event: ChangeEvent<HTMLTextAreaElement>) {
    onChange(event.target.value);
  }

  function focusLine(lineNumber: number) {
    const textarea = document.getElementById('review-markdown-editor') as HTMLTextAreaElement | null;
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
                      type="button"
                      variant="ghost"
                      onClick={() => handleToolbarClick(item.prefix, item.suffix)}
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
                size="icon"
                type="button"
                variant={mode === 'write' ? 'secondary' : 'ghost'}
                onClick={() => setMode('write')}
              >
                <PanelLeftClose className="size-4" />
              </Button>
              <Button
                aria-label={t('reviewEditor.split')}
                size="icon"
                type="button"
                variant={mode === 'split' ? 'secondary' : 'ghost'}
                onClick={() => setMode('split')}
              >
                <Split className="size-4" />
              </Button>
              <Button
                aria-label={t('reviewEditor.preview')}
                size="icon"
                type="button"
                variant={mode === 'preview' ? 'secondary' : 'ghost'}
                onClick={() => setMode('preview')}
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
                <button
                  data-depth={item.depth}
                  key={`${item.line}-${item.title}`}
                  type="button"
                  onClick={() => focusLine(item.line)}
                >
                  {item.title}
                </button>
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
            <textarea
              aria-label={t('reviewEditor.title')}
              className="review-editor-textarea"
              id="review-markdown-editor"
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
                <p className="text-sm text-neutral-500 dark:text-neutral-400">{t('reviewEditor.previewEmpty')}</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
