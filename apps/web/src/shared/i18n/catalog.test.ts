import ts from 'typescript';
import { describe, expect, it } from 'vitest';
import { locales, messages } from './catalog';

const sourceModules = import.meta.glob<string>('../../**/*.{ts,tsx}', {
  eager: true,
  import: 'default',
  query: '?raw',
});

function escapeRegularExpression(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function findMessageReferences() {
  const literalKeys = new Set<string>();
  const dynamicKeys: RegExp[] = [];

  for (const [path, sourceText] of Object.entries(sourceModules)) {
    if (path.includes('/i18n/catalogs/')) continue;

    const sourceFile = ts.createSourceFile(
      path,
      sourceText,
      ts.ScriptTarget.Latest,
      true,
      path.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
    );

    function visit(node: ts.Node) {
      if (ts.isStringLiteralLike(node)) literalKeys.add(node.text);

      if (
        ts.isCallExpression(node) &&
        ts.isIdentifier(node.expression) &&
        node.expression.text === 't' &&
        node.arguments[0] &&
        ts.isTemplateExpression(node.arguments[0])
      ) {
        const template = node.arguments[0];
        const fragments = [template.head.text, ...template.templateSpans.map(({ literal }) => literal.text)];
        dynamicKeys.push(new RegExp(`^${fragments.map(escapeRegularExpression).join('.*')}$`));
      }

      ts.forEachChild(node, visit);
    }

    visit(sourceFile);
  }

  return { dynamicKeys, literalKeys };
}

describe('translation catalogs', () => {
  it('contain the same keys for every locale', () => {
    const expectedKeys = Object.keys(messages['zh-CN']).sort();

    for (const locale of locales) {
      expect(Object.keys(messages[locale]).sort()).toEqual(expectedKeys);
    }
  });

  it('do not retain message keys without a source consumer', () => {
    const { dynamicKeys, literalKeys } = findMessageReferences();
    const unusedKeys = Object.keys(messages['zh-CN']).filter(
      (key) => !literalKeys.has(key) && !dynamicKeys.some((pattern) => pattern.test(key)),
    );

    expect(unusedKeys).toEqual([]);
  });
});
