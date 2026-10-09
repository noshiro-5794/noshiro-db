import ReactMarkdown, { defaultUrlTransform, type Components } from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';
import './markdown.css';

type MarkdownRendererProps = {
  content: string;
};

const rehypePlugins = [rehypeSanitize];
const remarkPlugins = [remarkGfm];
const markdownComponents = {
  a({ node, href, ...props }) {
    void node;
    const external = typeof href === 'string' && /^(?:https?:)?\/\//iu.test(href);
    return (
      <a {...props} href={href} {...(external ? { rel: 'nofollow noopener noreferrer ugc', target: '_blank' } : {})} />
    );
  },
  img({ node, ...props }) {
    void node;
    return <img {...props} decoding="async" loading="lazy" referrerPolicy="no-referrer" />;
  },
  h1({ node, ...props }) {
    void node;
    return (
      <h2 className="m-0 border-b border-border-subtle pb-2 pt-2 text-xl font-semibold leading-tight" {...props} />
    );
  },
  h2({ node, ...props }) {
    void node;
    return <h3 className="m-0 pt-2 text-lg font-semibold leading-tight" {...props} />;
  },
  h3({ node, ...props }) {
    void node;
    return <h4 className="m-0 pt-2 text-base font-semibold leading-tight" {...props} />;
  },
  h4({ node, ...props }) {
    void node;
    return <h5 className="m-0 pt-2 text-sm font-semibold leading-5" {...props} />;
  },
  h5({ node, ...props }) {
    void node;
    return <h6 className="m-0 pt-2 text-sm font-semibold leading-5" {...props} />;
  },
  h6({ node, ...props }) {
    void node;
    return <h6 className="m-0 pt-2 text-sm font-semibold leading-5" {...props} />;
  },
} satisfies Components;

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="markdown-body">
      <ReactMarkdown
        components={markdownComponents}
        rehypePlugins={rehypePlugins}
        remarkPlugins={remarkPlugins}
        urlTransform={defaultUrlTransform}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
