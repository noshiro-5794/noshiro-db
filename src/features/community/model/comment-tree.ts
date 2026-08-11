import type { CommunityCommentSummary } from '@/shared/api';

export type CommentNode = CommunityCommentSummary & {
  children: CommentNode[];
};

function wouldCreateCycle(child: CommentNode, parent: CommentNode, nodeMap: ReadonlyMap<number, CommentNode>) {
  const visited = new Set<number>();
  let current: CommentNode | undefined = parent;

  while (current) {
    if (current.id === child.id || visited.has(current.id)) return true;
    visited.add(current.id);
    current = current.parent_id ? nodeMap.get(current.parent_id) : undefined;
  }

  return false;
}

export function buildCommentTree(comments: readonly CommunityCommentSummary[]) {
  const nodeMap = new Map<number, CommentNode>();

  for (const comment of comments) {
    if (!nodeMap.has(comment.id)) nodeMap.set(comment.id, { ...comment, children: [] });
  }

  const roots: CommentNode[] = [];
  for (const node of nodeMap.values()) {
    const parent = node.parent_id ? nodeMap.get(node.parent_id) : undefined;
    if (!parent || wouldCreateCycle(node, parent, nodeMap)) roots.push(node);
    else parent.children.push(node);
  }

  return roots;
}
