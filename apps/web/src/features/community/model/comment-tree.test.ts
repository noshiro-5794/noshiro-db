import { describe, expect, it } from 'vitest';
import type { CommunityCommentSummary } from '@/shared/api';
import { buildCommentTree } from './comment-tree';

function comment(id: number, parentId?: number | null): CommunityCommentSummary {
  return {
    id,
    ...(parentId === undefined ? {} : { parent_id: parentId }),
    content: `comment ${id}`,
    visibility: 'public',
    is_spoiler: false,
  };
}

describe('buildCommentTree', () => {
  it('builds nested replies while preserving input order', () => {
    const tree = buildCommentTree([comment(1), comment(2, 1), comment(3), comment(4, 2)]);

    expect(tree.map((node) => node.id)).toEqual([1, 3]);
    expect(tree[0]?.children.map((node) => node.id)).toEqual([2]);
    expect(tree[0]?.children[0]?.children.map((node) => node.id)).toEqual([4]);
  });

  it('keeps orphaned and cyclic comments visible as roots', () => {
    const tree = buildCommentTree([comment(1, 2), comment(2, 1), comment(3, 999), comment(4, 4)]);

    expect(tree.map((node) => node.id)).toEqual([1, 2, 3, 4]);
    expect(tree.every((node) => node.children.length === 0)).toBe(true);
  });

  it('ignores duplicate IDs instead of duplicating recursive keys', () => {
    const tree = buildCommentTree([comment(1), { ...comment(1), content: 'duplicate' }]);

    expect(tree).toHaveLength(1);
    expect(tree[0]?.content).toBe('comment 1');
  });
});
