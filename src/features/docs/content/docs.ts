import type { Locale } from '@/features/i18n/messages';

export type DocsSection = {
  id: string;
  title: string;
  body: string[];
};

export type DocsPageContent = {
  slug: string;
  title: string;
  description: string;
  sections: DocsSection[];
};

export type DocsContent = {
  nav: Array<Pick<DocsPageContent, 'slug' | 'title'>>;
  pages: Record<string, DocsPageContent>;
};

export const defaultDocsSlug = 'introduction';

const nav = {
  'zh-CN': [
    { slug: 'introduction', title: '介绍' },
    { slug: 'guide', title: '使用指南' },
    { slug: 'reviews', title: '长评与 Markdown' },
    { slug: 'community', title: '社区与资料库' },
    { slug: 'graph', title: '知识图谱' },
    { slug: 'development', title: '开发说明' },
    { slug: 'changelog', title: '更新记录' },
  ],
  'en-US': [
    { slug: 'introduction', title: 'Introduction' },
    { slug: 'guide', title: 'Guide' },
    { slug: 'reviews', title: 'Reviews and Markdown' },
    { slug: 'community', title: 'Community and Library' },
    { slug: 'graph', title: 'Knowledge Graph' },
    { slug: 'development', title: 'Development' },
    { slug: 'changelog', title: 'Changelog' },
  ],
  'ja-JP': [
    { slug: 'introduction', title: '紹介' },
    { slug: 'guide', title: 'ガイド' },
    { slug: 'reviews', title: 'レビューと Markdown' },
    { slug: 'community', title: 'コミュニティとライブラリ' },
    { slug: 'graph', title: '知識グラフ' },
    { slug: 'development', title: '開発メモ' },
    { slug: 'changelog', title: '更新履歴' },
  ],
} satisfies Record<Locale, DocsContent['nav']>;

export const docsContent: Record<Locale, DocsContent> = {
  'zh-CN': {
    nav: nav['zh-CN'],
    pages: {
      introduction: {
        slug: 'introduction',
        title: 'Noshiro DB',
        description: '一个围绕动画与 Galgame 的个人数据库、资料库和轻量社区。',
        sections: [
          {
            id: 'purpose',
            title: '项目定位',
            body: [
              'Noshiro DB 用于浏览作品、记录观看和游玩状态、整理收藏集、撰写长评，并通过轻量社区内容发现更多条目。',
              '它是个人项目，但前端结构、API 边界、权限分层和视觉系统都按长期维护的产品标准设计。',
            ],
          },
          {
            id: 'access',
            title: '访问层级',
            body: [
              '未登录用户可以访问 Home、Search、Calendar、Subject 和 Docs。登录后会开放 Home 工作台、资料库、收藏集、Review、动态、通知、书签和设置。',
              '管理员拥有独立管理面板，用于同步 Bangumi 数据、维护索引以及查看系统状态。',
            ],
          },
          {
            id: 'principles',
            title: '设计原则',
            body: [
              '主题色只是强调色，整体主题以浅色、深色和自动模式为主。用户登录后可以设置语言、外观和强调色。',
              '页面以信息密度、可扫描性和长期使用体验为优先，只有知识图谱页承担更强的展示和探索性。',
            ],
          },
        ],
      },
      guide: {
        slug: 'guide',
        title: '使用指南',
        description: '从公开浏览到登录后的个人工作台，了解主要使用路径。',
        sections: [
          {
            id: 'discover',
            title: '发现作品',
            body: [
              'Home 提供公开的 Calendar 和 Search 展示。Search 初始使用 Calendar 数据，输入关键词后切换到数据库检索。',
              'Calendar 按星期展示放送条目，并使用热度数据辅助排序；Search 页面提供类型、年份、季度、平台、集数范围和排序等筛选。',
            ],
          },
          {
            id: 'subject',
            title: '作品详情',
            body: [
              'Subject 页面展示海报、基础信息、staff、episodes、characters、relations、Bangumi 外链和评分快照。',
              '登录后可以打开 Mark 弹窗，统一保存状态、评分、详细评分、标签、简评和观看进度。',
            ],
          },
          {
            id: 'workspace',
            title: '登录后的工作台',
            body: [
              'Home 工作台展示个人动态入口、资料库概览和后续 feed 布局。Me 页面以 GitHub 风格展示个人资料、贡献日历、Review 和时间线。',
              'Settings 用于账号资料、语言、外观、主题色和密码相关操作。',
            ],
          },
        ],
      },
      reviews: {
        slug: 'reviews',
        title: '长评与 Markdown',
        description: 'Review 是 Noshiro DB 的核心内容形态之一，支持独立浏览、编辑和作品页嵌入。',
        sections: [
          {
            id: 'storage',
            title: '存储与渲染',
            body: [
              '后端保存纯文本 Markdown，不保存渲染后的 HTML。这样便于迁移、备份和未来替换编辑器。',
              '前端使用 react-markdown、remark-gfm 和 rehype-sanitize 渲染内容，在支持表格、代码块、引用和链接的同时控制安全风险。',
            ],
          },
          {
            id: 'editor',
            title: '编辑体验',
            body: [
              'Review 编辑页采用写作和预览并行的体验，目标接近 Obsidian 风格的实时编辑，但保持网页端操作简洁。',
              'Review 可以标记公开、剧透和关联作品；自己的 Review 可以从详情页或 Review 浏览页进入编辑。',
            ],
          },
          {
            id: 'reading',
            title: '浏览与社区',
            body: [
              '作品页展示当前条目的公开 Reviews，并包含作者信息、剧透状态、更新时间和操作入口。',
              'Reviews 页面和 Bookmarks 页面使用统一的社区内容卡片风格，方便浏览、收藏和继续阅读。',
            ],
          },
        ],
      },
      community: {
        slug: 'community',
        title: '社区与资料库',
        description: '社区能力围绕作品、Review、Collection 和 Activity 展开，而不是传统论坛。',
        sections: [
          {
            id: 'library',
            title: '资料库',
            body: [
              'Library 用于筛选和整理自己标记过的作品，支持状态、评分、标签、排序和分页。',
              '用户标签不是独立创建的全局分类，而是在作品标记中填写后自动沉淀，适合个人资料管理。',
            ],
          },
          {
            id: 'collections',
            title: '收藏集',
            body: [
              'Collections 用于打包展示一组已标记作品。左侧是收藏集封面，右侧横向滚动展示条目，并支持拖拽排序。',
              '添加条目时从 Library 中搜索选择，避免把未标记作品直接塞入收藏集。',
            ],
          },
          {
            id: 'community',
            title: '轻量社区',
            body: [
              'Community Posts、评论、关注、通知、书签和公开用户页已经接入前端结构。',
              '社区内容围绕作品和用户行为展开，目标是辅助发现和记录，而不是取代数据库本身。',
            ],
          },
        ],
      },
      graph: {
        slug: 'graph',
        title: '知识图谱',
        description: 'Subject 知识图谱是全站唯一强调探索和展示效果的页面。',
        sections: [
          {
            id: 'data',
            title: '数据来源',
            body: [
              '图谱从 subject、episodes、staff、characters、actors、relations、tags 和 metadata 构建节点与关系。',
              '默认使用精选模式以保证流畅度；切换为全部模式会追分页加载更多数据，适合分析大型条目。',
            ],
          },
          {
            id: 'layout',
            title: '布局算法',
            body: [
              '图谱使用前端 Canvas 渲染和自定义力导向布局。节点之间存在排斥力，关系边作为弹簧约束，subject 节点保持在视觉中心附近。',
              '布局不会按类型强制分成固定簇，而是通过关系自然形成拓扑结构，并使用软边界和径向约束避免节点贴边。',
            ],
          },
          {
            id: 'interaction',
            title: '交互',
            body: [
              '支持拖拽节点、平移画布、滚轮缩放、适配视图、重置视图、悬停高亮和右下详情卡。',
              '只有 anime 和 galgame 类型的 subject 节点提供打开详情页的入口，其他外部关系只展示信息。',
            ],
          },
        ],
      },
      development: {
        slug: 'development',
        title: '开发说明',
        description: 'Noshiro DB Frontend 使用 React、TypeScript、Vite、TanStack Query、Tailwind CSS 和 Radix primitives。',
        sections: [
          {
            id: 'structure',
            title: '项目结构',
            body: [
              'app 放应用壳和全局 provider，features 放领域模块，lib 放 API client、query client 等技术基础设施，pages 放路由页面，shared/ui 放无领域归属的 UI primitives。',
              'API 请求和 React Query options 按 feature 就近维护，避免所有接口集中在一个大文件里。',
            ],
          },
          {
            id: 'environment',
            title: '本地环境',
            body: [
              '复制 .env.example 为 .env，配置 VITE_API_BASE_URL 和 VITE_HCAPTCHA_SITE_KEY。',
              '远程 SSH 开发时，Vite 需要使用 --host 0.0.0.0，同时确保前端端口和后端端口都被 SSH tunnel 转发。',
            ],
          },
          {
            id: 'checks',
            title: '提交前检查',
            body: [
              '提交前建议运行 npm run typecheck、npm run lint 和 npm run build。',
              'dist、node_modules、tsbuildinfo 和 .env 都不应该提交；公开静态资源、README、docs 和 .env.example 应保留。',
            ],
          },
        ],
      },
      changelog: {
        slug: 'changelog',
        title: '更新记录',
        description: '记录当前前端已经具备的主要能力。',
        sections: [
          {
            id: 'public',
            title: '公开页面',
            body: [
              '完成 Home、Search、Calendar、Subject、Docs、Login、Register 和 Reset Password 页面。',
              'Search 和 Calendar 已统一筛选、分页、跳页、展示卡片和多语言文本。',
            ],
          },
          {
            id: 'workspace',
            title: '登录态工作区',
            body: [
              '完成个人 Home、Me、Settings、Library、Collections、Reviews、Bookmarks、Notifications 和公开用户相关页面。',
              '接入社区 posts、comments、reactions、bookmarks、reports、follow、feed 和 activities 相关接口。',
            ],
          },
          {
            id: 'admin-graph',
            title: '管理与图谱',
            body: [
              '完成管理员首页、同步入口和 Bangumi 单条同步前端入口。',
              '完成 Subject 知识图谱页面，包含 Canvas 可视化、筛选面板、缩放工具、详情卡和全屏展示。',
            ],
          },
        ],
      },
    },
  },
  'en-US': {
    nav: nav['en-US'],
    pages: {
      introduction: {
        slug: 'introduction',
        title: 'Noshiro DB',
        description: 'A personal anime and galgame database, library, and lightweight community.',
        sections: [
          {
            id: 'purpose',
            title: 'Purpose',
            body: [
              'Noshiro DB is built for browsing titles, recording watch and play status, organizing collections, writing reviews, and discovering content through a restrained community layer.',
              'It is a personal project, but the frontend architecture, API boundaries, permission model, and visual system are designed for long-term maintenance.',
            ],
          },
          {
            id: 'access',
            title: 'Access levels',
            body: [
              'Anonymous users can access Home, Search, Calendar, Subject, and Docs. Signed-in users can access the workspace Home, Library, Collections, Reviews, Feed-related pages, Notifications, Bookmarks, and Settings.',
              'Admins have a separate panel for Bangumi sync, index maintenance, and system operations.',
            ],
          },
          {
            id: 'principles',
            title: 'Design principles',
            body: [
              'The accent color is treated like a system accent, while light, dark, and auto modes define the main theme. Signed-in users can customize language, appearance, and accent color.',
              'Most pages prioritize density, scanning, and repeated use. The knowledge graph is the only page intentionally designed for stronger visual exploration.',
            ],
          },
        ],
      },
      guide: {
        slug: 'guide',
        title: 'Guide',
        description: 'Understand the main path from public discovery to the signed-in workspace.',
        sections: [
          {
            id: 'discover',
            title: 'Discover titles',
            body: [
              'Home provides public Calendar and Search showcases. Search defaults to Calendar data, then switches to full database search after a keyword is submitted.',
              'Calendar groups airing titles by weekday and uses heat data for ordering. Search supports type, year, season, platform, episode ranges, and ordering.',
            ],
          },
          {
            id: 'subject',
            title: 'Subject detail',
            body: [
              'Subject pages show poster, metadata, staff, episodes, characters, relations, Bangumi link, and score snapshot.',
              'After signing in, users can open the Mark dialog and save status, ratings, rating details, tags, short comments, and progress in one place.',
            ],
          },
          {
            id: 'workspace',
            title: 'Workspace',
            body: [
              'The signed-in Home prepares the personal feed layout and workspace summaries. Me uses a GitHub-like profile layout with contribution calendar, reviews, and timeline.',
              'Settings handles account profile, language, appearance, accent color, and password-related flows.',
            ],
          },
        ],
      },
      reviews: {
        slug: 'reviews',
        title: 'Reviews and Markdown',
        description: 'Reviews are a core content type, with standalone reading, editing, and subject-page embedding.',
        sections: [
          {
            id: 'storage',
            title: 'Storage and rendering',
            body: [
              'The backend stores plain Markdown text instead of rendered HTML, keeping reviews portable and easy to migrate.',
              'The frontend renders with react-markdown, remark-gfm, and rehype-sanitize to support tables, code blocks, quotes, and links while controlling security risk.',
            ],
          },
          {
            id: 'editor',
            title: 'Editor experience',
            body: [
              'The editor uses a writing-and-preview layout inspired by realtime Markdown tools, while staying simple for the web.',
              'Reviews can be public, spoiler-marked, and linked to subjects. Own reviews can be edited from detail and viewer pages.',
            ],
          },
          {
            id: 'reading',
            title: 'Reading and community',
            body: [
              'Subject pages show public reviews with author, spoiler state, update time, and action entry points.',
              'Reviews and Bookmarks pages share a unified community content card style for reading, saving, and revisiting.',
            ],
          },
        ],
      },
      community: {
        slug: 'community',
        title: 'Community and Library',
        description: 'Community features center on subjects, reviews, collections, and activities rather than a traditional forum.',
        sections: [
          {
            id: 'library',
            title: 'Library',
            body: [
              'Library helps users filter and organize marked subjects by status, rating, tags, ordering, and pagination.',
              'Tags are not manually created global categories. They are collected from user subject marks and work as personal organization labels.',
            ],
          },
          {
            id: 'collections',
            title: 'Collections',
            body: [
              'Collections package marked subjects into visual sets. The left side shows the selected collection cover, while the right side uses a horizontal sortable item rail.',
              'Items are added by searching the user Library, preventing unmarked subjects from being inserted directly.',
            ],
          },
          {
            id: 'community',
            title: 'Light community',
            body: [
              'Community Posts, comments, follows, notifications, bookmarks, and public user pages are wired into the frontend structure.',
              'Community content is designed to support discovery and record keeping, not to replace the database.',
            ],
          },
        ],
      },
      graph: {
        slug: 'graph',
        title: 'Knowledge Graph',
        description: 'The Subject knowledge graph is the only page intentionally optimized for visual exploration.',
        sections: [
          {
            id: 'data',
            title: 'Data source',
            body: [
              'The graph builds nodes and edges from subject, episodes, staff, characters, actors, relations, tags, and metadata.',
              'Curated mode is the default for performance. All mode follows pagination and loads more data for larger analysis sessions.',
            ],
          },
          {
            id: 'layout',
            title: 'Layout algorithm',
            body: [
              'The page uses Canvas rendering and a custom force-directed layout. Nodes repel each other, relation edges act as springs, and the subject node stays near the visual center.',
              'The layout does not force fixed type clusters. It lets topology emerge from relationships while soft boundaries and radial constraints prevent edge crowding.',
            ],
          },
          {
            id: 'interaction',
            title: 'Interaction',
            body: [
              'The graph supports node dragging, canvas panning, wheel zooming, fit view, reset view, hover highlighting, and a detail card.',
              'Only anime and galgame subject nodes expose an open-detail action; other relation nodes display information only.',
            ],
          },
        ],
      },
      development: {
        slug: 'development',
        title: 'Development',
        description: 'Noshiro DB Frontend uses React, TypeScript, Vite, TanStack Query, Tailwind CSS, and Radix primitives.',
        sections: [
          {
            id: 'structure',
            title: 'Project structure',
            body: [
              'app owns the application shell and providers, features own product domains, lib owns API and query infrastructure, pages own route composition, and shared/ui owns domain-free UI primitives.',
              'Feature API wrappers and React Query options stay near their domain, keeping pages focused on composition and user flow.',
            ],
          },
          {
            id: 'environment',
            title: 'Local environment',
            body: [
              'Copy .env.example to .env, then set VITE_API_BASE_URL and VITE_HCAPTCHA_SITE_KEY.',
              'For SSH development, run Vite with --host 0.0.0.0 and make sure both frontend and backend ports are forwarded through the SSH tunnel.',
            ],
          },
          {
            id: 'checks',
            title: 'Pre-commit checks',
            body: [
              'Run npm run typecheck, npm run lint, and npm run build before committing.',
              'dist, node_modules, tsbuildinfo, and .env should not be committed. Public static assets, README, docs, and .env.example should remain in the repository.',
            ],
          },
        ],
      },
      changelog: {
        slug: 'changelog',
        title: 'Changelog',
        description: 'A concise record of the major frontend capabilities already implemented.',
        sections: [
          {
            id: 'public',
            title: 'Public pages',
            body: [
              'Completed Home, Search, Calendar, Subject, Docs, Login, Register, and Reset Password pages.',
              'Search and Calendar now share polished filtering, pagination, jump-to-page, result cards, and multilingual text.',
            ],
          },
          {
            id: 'workspace',
            title: 'Signed-in workspace',
            body: [
              'Completed Home, Me, Settings, Library, Collections, Reviews, Bookmarks, Notifications, and public user pages.',
              'Connected community posts, comments, reactions, bookmarks, reports, follow, feed, and activity APIs.',
            ],
          },
          {
            id: 'admin-graph',
            title: 'Admin and graph',
            body: [
              'Completed Admin dashboard, sync entry points, and Bangumi single-subject sync UI.',
              'Completed Subject knowledge graph with Canvas visualization, data controls, zoom tools, detail card, and fullscreen presentation.',
            ],
          },
        ],
      },
    },
  },
  'ja-JP': {
    nav: nav['ja-JP'],
    pages: {
      introduction: {
        slug: 'introduction',
        title: 'Noshiro DB',
        description: 'アニメとギャルゲームを中心にした個人データベース、ライブラリ、軽量コミュニティです。',
        sections: [
          {
            id: 'purpose',
            title: '目的',
            body: [
              'Noshiro DB は作品を探し、視聴・プレイ状況を記録し、コレクションを整理し、レビューを書き、軽量なコミュニティから発見するための場所です。',
              '個人プロジェクトですが、フロントエンド構造、API 境界、権限設計、ビジュアルシステムは長期運用を前提に作られています。',
            ],
          },
          {
            id: 'access',
            title: 'アクセス範囲',
            body: [
              '未ログインでは Home、Search、Calendar、Subject、Docs を利用できます。ログイン後はワークスペース、Library、Collections、Reviews、通知、ブックマーク、設定などが使えます。',
              '管理者には Bangumi 同期、インデックス保守、システム操作のための専用パネルがあります。',
            ],
          },
          {
            id: 'principles',
            title: 'デザイン方針',
            body: [
              'アクセントカラーはシステムアクセントのように扱い、全体テーマはライト、ダーク、オートを基本にします。ログイン後は言語、外観、アクセントカラーを変更できます。',
              '多くのページは情報密度、スキャンしやすさ、継続利用を重視します。知識グラフだけは探索性と展示性を強めたページです。',
            ],
          },
        ],
      },
      guide: {
        slug: 'guide',
        title: 'ガイド',
        description: '公開ページでの発見からログイン後のワークスペースまで、主な流れを説明します。',
        sections: [
          {
            id: 'discover',
            title: '作品を探す',
            body: [
              'Home では Calendar と Search の公開表示を提供します。Search は初期状態で Calendar データを使い、キーワード入力後に全データベース検索へ切り替わります。',
              'Calendar は曜日ごとに放送作品を整理し、熱度データで並び替えます。Search では種類、年、クール、プラットフォーム、話数範囲、並び順を指定できます。',
            ],
          },
          {
            id: 'subject',
            title: '作品詳細',
            body: [
              'Subject ページではポスター、基本情報、staff、episodes、characters、relations、Bangumi リンク、スコアスナップショットを表示します。',
              'ログイン後は Mark ダイアログから状態、評価、詳細評価、タグ、短いコメント、進捗をまとめて保存できます。',
            ],
          },
          {
            id: 'workspace',
            title: 'ワークスペース',
            body: [
              'ログイン後の Home は個人フィードとワークスペース概要の入口になります。Me は GitHub 風のプロフィール、貢献カレンダー、レビュー、タイムラインを表示します。',
              'Settings ではプロフィール、言語、外観、アクセントカラー、パスワード関連の操作を扱います。',
            ],
          },
        ],
      },
      reviews: {
        slug: 'reviews',
        title: 'レビューと Markdown',
        description: 'Review は独立した閲覧、編集、作品ページへの埋め込みに対応する主要コンテンツです。',
        sections: [
          {
            id: 'storage',
            title: '保存と表示',
            body: [
              'バックエンドにはレンダリング済み HTML ではなく、プレーンな Markdown テキストを保存します。これにより移行やバックアップがしやすくなります。',
              'フロントエンドは react-markdown、remark-gfm、rehype-sanitize を使い、表、コードブロック、引用、リンクを表示しつつ安全性を保ちます。',
            ],
          },
          {
            id: 'editor',
            title: '編集体験',
            body: [
              'エディタはリアルタイム Markdown ツールに近い書く画面とプレビューの構成を持ち、Web で使いやすい軽さを保ちます。',
              'Review は公開、ネタバレ、関連作品を設定できます。自分の Review は詳細ページや閲覧ページから編集できます。',
            ],
          },
          {
            id: 'reading',
            title: '閲覧とコミュニティ',
            body: [
              '作品ページでは公開 Reviews を作者、ネタバレ状態、更新日時、操作入口とともに表示します。',
              'Reviews と Bookmarks は統一されたコミュニティカードで表示し、読み返しや保存をしやすくします。',
            ],
          },
        ],
      },
      community: {
        slug: 'community',
        title: 'コミュニティとライブラリ',
        description: 'コミュニティ機能は従来型フォーラムではなく、作品、Review、Collection、Activity を中心にしています。',
        sections: [
          {
            id: 'library',
            title: 'Library',
            body: [
              'Library は記録した作品を状態、評価、タグ、並び順、ページングで整理するためのページです。',
              'タグはグローバルに手動作成するものではなく、作品記録に入力した内容から個人用ラベルとして蓄積されます。',
            ],
          },
          {
            id: 'collections',
            title: 'Collections',
            body: [
              'Collections は記録済み作品を視覚的なセットにまとめます。左側に選択したコレクションのカバー、右側に横スクロール可能な並び替えレールを表示します。',
              '項目追加は Library から検索して選ぶため、未記録作品を直接入れることはありません。',
            ],
          },
          {
            id: 'community',
            title: '軽量コミュニティ',
            body: [
              'Community Posts、コメント、フォロー、通知、ブックマーク、公開ユーザーページはフロントエンド構造に接続されています。',
              'コミュニティコンテンツは発見と記録を補助するもので、データベース本体を置き換えるものではありません。',
            ],
          },
        ],
      },
      graph: {
        slug: 'graph',
        title: '知識グラフ',
        description: 'Subject 知識グラフは、全体の中で視覚探索に特化したページです。',
        sections: [
          {
            id: 'data',
            title: 'データソース',
            body: [
              'グラフは subject、episodes、staff、characters、actors、relations、tags、metadata からノードとエッジを構築します。',
              '通常は動作を優先した厳選モードを使います。すべてモードではページングを追跡してより多くのデータを読み込みます。',
            ],
          },
          {
            id: 'layout',
            title: 'レイアウト',
            body: [
              'Canvas 描画と独自の力指向レイアウトを使います。ノードは反発し、関係エッジはばねとして働き、subject は視覚中心付近に保たれます。',
              '種類ごとの固定クラスタにはせず、関係から自然に構造を作ります。ソフト境界と半径制約で端に寄りすぎないようにしています。',
            ],
          },
          {
            id: 'interaction',
            title: '操作',
            body: [
              'ノードドラッグ、キャンバス移動、ホイールズーム、画面に合わせる、リセット、ホバー強調、詳細カードを利用できます。',
              'anime と galgame の subject ノードだけが詳細ページを開けます。それ以外の関連ノードは情報表示のみです。',
            ],
          },
        ],
      },
      development: {
        slug: 'development',
        title: '開発メモ',
        description: 'Noshiro DB Frontend は React、TypeScript、Vite、TanStack Query、Tailwind CSS、Radix primitives を使っています。',
        sections: [
          {
            id: 'structure',
            title: '構造',
            body: [
              'app はアプリケーションシェルと provider、features はドメイン、lib は API と query の基盤、pages はルート構成、shared/ui はドメインを持たない UI primitive を担当します。',
              'API ラッパーと React Query options は feature ごとに近くへ置き、pages は構成とユーザーフローに集中します。',
            ],
          },
          {
            id: 'environment',
            title: 'ローカル環境',
            body: [
              '.env.example を .env にコピーし、VITE_API_BASE_URL と VITE_HCAPTCHA_SITE_KEY を設定します。',
              'SSH 開発では Vite を --host 0.0.0.0 で起動し、フロントエンドとバックエンドの両方のポートをトンネルしてください。',
            ],
          },
          {
            id: 'checks',
            title: 'コミット前チェック',
            body: [
              'コミット前に npm run typecheck、npm run lint、npm run build を実行することを推奨します。',
              'dist、node_modules、tsbuildinfo、.env はコミットしません。公開静的ファイル、README、docs、.env.example は残します。',
            ],
          },
        ],
      },
      changelog: {
        slug: 'changelog',
        title: '更新履歴',
        description: '現在実装されている主なフロントエンド機能をまとめます。',
        sections: [
          {
            id: 'public',
            title: '公開ページ',
            body: [
              'Home、Search、Calendar、Subject、Docs、Login、Register、Reset Password を実装しました。',
              'Search と Calendar はフィルタ、ページング、ページ移動、結果カード、多言語テキストを統一しています。',
            ],
          },
          {
            id: 'workspace',
            title: 'ログイン後ワークスペース',
            body: [
              'Home、Me、Settings、Library、Collections、Reviews、Bookmarks、Notifications、公開ユーザーページを実装しました。',
              'community posts、comments、reactions、bookmarks、reports、follow、feed、activities API に接続しています。',
            ],
          },
          {
            id: 'admin-graph',
            title: '管理とグラフ',
            body: [
              'Admin ダッシュボード、同期入口、Bangumi 単体同期 UI を実装しました。',
              'Subject 知識グラフには Canvas 可視化、データ制御、ズームツール、詳細カード、全画面表示があります。',
            ],
          },
        ],
      },
    },
  },
};
