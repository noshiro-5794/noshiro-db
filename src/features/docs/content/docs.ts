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

export const docsContent: Record<Locale, DocsContent> = {
  'zh-CN': {
    nav: [
      { slug: 'introduction', title: '介绍' },
      { slug: 'guide', title: '使用指南' },
      { slug: 'reviews', title: 'Review 与 Markdown' },
      { slug: 'roadmap', title: '路线图' },
      { slug: 'changelog', title: '更新记录' },
    ],
    pages: {
      introduction: {
        slug: 'introduction',
        title: '介绍',
        description: 'Noshiro DB 是一个用于浏览、收藏、记录和重温动画与 Galgame 的个人数据库。',
        sections: [
          {
            id: 'what-is-noshiro-db',
            title: 'Noshiro DB 是什么',
            body: [
              'Noshiro DB 面向动画与 Galgame。它既是作品索引，也会成为你的收藏、进度、评分、评论和 collection 工作区。',
              '这个项目保留 Noshiro 的个人特色，但设计方式会尽量接近商业产品：稳定的 API、清晰的信息架构、可维护的前端结构，以及适合多端使用的界面。',
            ],
          },
          {
            id: 'current-stage',
            title: '当前阶段',
            body: [
              '公开页面已经包含首页、每周日历、搜索、作品详情骨架和文档入口。',
              '接下来会优先完善登录、注册、个人资料库、收藏状态、进度和 Review 的完整交互。',
            ],
          },
        ],
      },
      guide: {
        slug: 'guide',
        title: '使用指南',
        description: '从公开浏览到登录后的个人资料库，了解 Noshiro DB 的主要使用路径。',
        sections: [
          {
            id: 'browse',
            title: '浏览与发现',
            body: [
              '首页展示每周热门条目和搜索入口，适合快速发现近期值得关注的作品。',
              'Search 页面默认展示 Calendar 数据，输入关键词后切换到完整数据库搜索，避免首页搜索结果过于杂乱。',
            ],
          },
          {
            id: 'calendar',
            title: 'Calendar',
            body: [
              'Calendar 页面按星期组织放送作品，并使用热度数据辅助排序。',
              '这个模块主要用于发现本周正在播出的动画，因此星期信息只在 Calendar 场景中突出展示。',
            ],
          },
          {
            id: 'library',
            title: '登录后的资料库',
            body: [
              '登录后会逐步开放收藏状态、观看进度、评分、标签和个人备注。',
              '普通用户与管理员会看到不同入口，管理员还会拥有同步与维护相关的控制能力。',
            ],
          },
        ],
      },
      reviews: {
        slug: 'reviews',
        title: 'Review 与 Markdown',
        description: 'Review 会以 Markdown 存储，并以安全、现代的方式渲染。',
        sections: [
          {
            id: 'storage',
            title: '存储方式',
            body: [
              '后端存储纯文本 Markdown，不把渲染后的 HTML 写入数据库。',
              '这样可以让内容长期可迁移，也方便以后替换编辑器、渲染器或导出格式。',
            ],
          },
          {
            id: 'rendering',
            title: '渲染方式',
            body: [
              '前端已经准备了基于 react-markdown、remark-gfm 和 rehype-sanitize 的安全渲染层。',
              '后续会支持标题、列表、引用、表格、代码块、链接等常用 Markdown 能力，并让 Review 可以自然嵌入作品页。',
            ],
          },
          {
            id: 'editor',
            title: '编辑器方向',
            body: [
              '编辑器建议先做简洁的双栏写作与预览，再逐步加入自动保存、草稿、快捷工具栏和发布状态。',
              '目标不是做复杂 CMS，而是做一个适合认真写长评的轻量博客式体验。',
            ],
          },
        ],
      },
      roadmap: {
        slug: 'roadmap',
        title: '路线图',
        description: 'Noshiro DB 会按公开浏览、认证、个人资料库、Review、社区能力的顺序推进。',
        sections: [
          {
            id: 'public',
            title: '公开浏览',
            body: [
              '首页、Search、Calendar、作品详情和 Docs 是未登录用户的主要入口。',
              '这一阶段重点是信息展示、视觉风格和基础 API 返回结构稳定。',
            ],
          },
          {
            id: 'account',
            title: '账号与资料库',
            body: [
              '下一阶段会完善登录、注册、长期登录状态、个人主页和资料库管理。',
              '完成后再接入标记作品、删除标记、进度替换、评分和 Review 创建等登录态操作。',
            ],
          },
          {
            id: 'community',
            title: '轻量社区',
            body: [
              '后续会围绕公开 profile、activity feed、review 和 collection 做轻量发现。',
              '社区能力会保持克制，不抢走作品数据库和个人记录这两个核心目标。',
            ],
          },
        ],
      },
      changelog: {
        slug: 'changelog',
        title: '更新记录',
        description: '记录前端公开页面、API 接入和后续功能的关键变化。',
        sections: [
          {
            id: 'public-pages',
            title: '公开页面骨架',
            body: [
              '完成首页 Hero、Calendar 展示、Search 展示、Search 独立页面、Calendar 独立页面和 Docs 入口。',
              '统一了 Tailwind + Radix 风格的 UI 基础设施，并替换了浏览器原生下拉控件。',
            ],
          },
          {
            id: 'api-layer',
            title: 'API 请求层',
            body: [
              '完成认证、作品、日历、资料库、同步和社交相关 API 的前端类型与请求封装。',
              'Search 已支持分页、跳页、年份、季度、平台、集数、内容策略和排序等筛选。',
            ],
          },
        ],
      },
    },
  },
  'en-US': {
    nav: [
      { slug: 'introduction', title: 'Introduction' },
      { slug: 'guide', title: 'Guide' },
      { slug: 'reviews', title: 'Reviews and Markdown' },
      { slug: 'roadmap', title: 'Roadmap' },
      { slug: 'changelog', title: 'Changelog' },
    ],
    pages: {
      introduction: {
        slug: 'introduction',
        title: 'Introduction',
        description: 'Noshiro DB is a personal database for browsing, collecting, tracking, and revisiting anime and galgame titles.',
        sections: [
          {
            id: 'what-is-noshiro-db',
            title: 'What is Noshiro DB',
            body: [
              'Noshiro DB is built for anime and galgame titles. It works as a subject index and will grow into a workspace for library status, progress, ratings, reviews, and collections.',
              'The project keeps a personal Noshiro identity while aiming for product-grade structure: stable APIs, clear information architecture, maintainable frontend layers, and responsive interfaces.',
            ],
          },
          {
            id: 'current-stage',
            title: 'Current stage',
            body: [
              'Public pages now include the home page, weekly calendar, search, subject detail skeleton, and docs entry.',
              'The next work should focus on login, registration, the personal library, collection status, progress, and the full Review flow.',
            ],
          },
        ],
      },
      guide: {
        slug: 'guide',
        title: 'Guide',
        description: 'Learn the main paths from public discovery to the signed-in personal library.',
        sections: [
          {
            id: 'browse',
            title: 'Browse and discover',
            body: [
              'The home page highlights weekly items and a search entry for quick discovery.',
              'Search defaults to Calendar data, then switches to the full database after a keyword is submitted to keep the default result set focused.',
            ],
          },
          {
            id: 'calendar',
            title: 'Calendar',
            body: [
              'The Calendar page groups airing titles by weekday and uses heat data to make popular entries easier to scan.',
              'Weekday information is emphasized in Calendar contexts only, so search results can stay title-focused.',
            ],
          },
          {
            id: 'library',
            title: 'Signed-in library',
            body: [
              'After login, library status, progress, ratings, tags, and private notes will be connected gradually.',
              'Regular users and admins will see different entry points, with admin-only sync and maintenance controls.',
            ],
          },
        ],
      },
      reviews: {
        slug: 'reviews',
        title: 'Reviews and Markdown',
        description: 'Reviews are stored as Markdown and rendered safely on the frontend.',
        sections: [
          {
            id: 'storage',
            title: 'Storage',
            body: [
              'The backend stores plain Markdown text instead of rendered HTML.',
              'This keeps reviews portable and makes it easier to replace the editor, renderer, or export format later.',
            ],
          },
          {
            id: 'rendering',
            title: 'Rendering',
            body: [
              'The frontend already has a safe rendering layer based on react-markdown, remark-gfm, and rehype-sanitize.',
              'Future rendering will support headings, lists, quotes, tables, code blocks, and links while fitting naturally into subject pages.',
            ],
          },
          {
            id: 'editor',
            title: 'Editor direction',
            body: [
              'The editor should start with a clean writing and preview layout, then add autosave, drafts, a compact toolbar, and publishing states.',
              'The goal is not a heavy CMS, but a lightweight blog-like writing experience for thoughtful long-form reviews.',
            ],
          },
        ],
      },
      roadmap: {
        slug: 'roadmap',
        title: 'Roadmap',
        description: 'Noshiro DB will move through public discovery, auth, personal library, reviews, and lightweight community features.',
        sections: [
          {
            id: 'public',
            title: 'Public discovery',
            body: [
              'Home, Search, Calendar, Subject detail, and Docs are the main public entry points.',
              'This stage focuses on presentation, visual direction, and stable API response shapes.',
            ],
          },
          {
            id: 'account',
            title: 'Account and library',
            body: [
              'The next stage should complete login, registration, persistent sessions, profile pages, and library management.',
              'After that, signed-in actions such as marking subjects, deleting marks, replacing progress, ratings, and creating reviews can be connected to real pages.',
            ],
          },
          {
            id: 'community',
            title: 'Light community',
            body: [
              'Later work can add discovery through public profiles, activity feeds, reviews, and collections.',
              'Community features should stay restrained so the product remains centered on the database and personal records.',
            ],
          },
        ],
      },
      changelog: {
        slug: 'changelog',
        title: 'Changelog',
        description: 'A concise record of public pages, API wiring, and future feature changes.',
        sections: [
          {
            id: 'public-pages',
            title: 'Public page skeleton',
            body: [
              'Completed the home hero, Calendar showcase, Search showcase, standalone Search page, standalone Calendar page, and Docs entry.',
              'Unified the UI foundation around Tailwind and Radix-style primitives, replacing native browser selects.',
            ],
          },
          {
            id: 'api-layer',
            title: 'API layer',
            body: [
              'Frontend types and request wrappers now cover auth, subjects, calendar, library, sync, and social APIs.',
              'Search supports pagination, page jumping, year, season, platform, episode ranges, content visibility, and ordering.',
            ],
          },
        ],
      },
    },
  },
  'ja-JP': {
    nav: [
      { slug: 'introduction', title: '紹介' },
      { slug: 'guide', title: 'ガイド' },
      { slug: 'reviews', title: 'Review と Markdown' },
      { slug: 'roadmap', title: 'ロードマップ' },
      { slug: 'changelog', title: '更新履歴' },
    ],
    pages: {
      introduction: {
        slug: 'introduction',
        title: '紹介',
        description: 'Noshiro DB は、アニメとギャルゲームを探し、集め、記録し、振り返るための個人データベースです。',
        sections: [
          {
            id: 'what-is-noshiro-db',
            title: 'Noshiro DB とは',
            body: [
              'Noshiro DB はアニメとギャルゲームのためのデータベースです。作品インデックスとして使えるだけでなく、ライブラリ、進捗、評価、レビュー、collection のワークスペースになります。',
              'Noshiro らしい個人性を残しつつ、安定した API、明確な情報設計、保守しやすいフロントエンド、多端末に向いた UI を目指します。',
            ],
          },
          {
            id: 'current-stage',
            title: '現在の段階',
            body: [
              '公開ページにはホーム、週間カレンダー、検索、作品詳細の骨格、ドキュメント入口があります。',
              '次はログイン、登録、個人ライブラリ、collection 状態、進捗、Review の流れを優先します。',
            ],
          },
        ],
      },
      guide: {
        slug: 'guide',
        title: 'ガイド',
        description: '公開ページでの発見からログイン後の個人ライブラリまで、主な使い方をまとめます。',
        sections: [
          {
            id: 'browse',
            title: '探す',
            body: [
              'ホームでは週間作品と検索入口を表示し、最近の作品をすばやく見つけられます。',
              'Search は初期状態で Calendar データを表示し、キーワード入力後に全データベース検索へ切り替わります。',
            ],
          },
          {
            id: 'calendar',
            title: 'Calendar',
            body: [
              'Calendar は曜日ごとに放送作品を整理し、熱度データで注目作品を見つけやすくします。',
              '曜日情報は Calendar でだけ強調し、検索結果では作品情報を中心に見せます。',
            ],
          },
          {
            id: 'library',
            title: 'ログイン後のライブラリ',
            body: [
              'ログイン後、状態、進捗、評価、タグ、個人メモを段階的に接続します。',
              '一般ユーザーと管理者で入口を分け、管理者には同期やメンテナンス用の操作を用意します。',
            ],
          },
        ],
      },
      reviews: {
        slug: 'reviews',
        title: 'Review と Markdown',
        description: 'Review は Markdown として保存し、フロントエンドで安全に表示します。',
        sections: [
          {
            id: 'storage',
            title: '保存方式',
            body: [
              'バックエンドにはレンダリング済み HTML ではなく、プレーンな Markdown テキストを保存します。',
              'これにより移行しやすく、将来エディタやレンダラー、エクスポート形式を変更しやすくなります。',
            ],
          },
          {
            id: 'rendering',
            title: '表示方式',
            body: [
              'フロントエンドには react-markdown、remark-gfm、rehype-sanitize を使った安全な表示層があります。',
              '今後は見出し、リスト、引用、表、コードブロック、リンクなどに対応し、作品ページに自然に組み込みます。',
            ],
          },
          {
            id: 'editor',
            title: 'エディタの方向性',
            body: [
              'まずは書く画面とプレビューをシンプルに作り、その後オートセーブ、下書き、ツールバー、公開状態を追加します。',
              '重い CMS ではなく、長文 Review を気持ちよく書ける軽量ブログのような体験を目指します。',
            ],
          },
        ],
      },
      roadmap: {
        slug: 'roadmap',
        title: 'ロードマップ',
        description: '公開ページ、認証、個人ライブラリ、Review、軽量コミュニティの順で進めます。',
        sections: [
          {
            id: 'public',
            title: '公開ページ',
            body: [
              'ホーム、Search、Calendar、作品詳細、Docs が未ログインユーザーの主な入口です。',
              'この段階では表示、ビジュアルの方向性、API レスポンスの安定を重視します。',
            ],
          },
          {
            id: 'account',
            title: 'アカウントとライブラリ',
            body: [
              '次の段階でログイン、登録、永続セッション、プロフィール、ライブラリ管理を完成させます。',
              'その後、作品マーク、削除、進捗更新、評価、Review 作成などのログイン操作を画面につなぎます。',
            ],
          },
          {
            id: 'community',
            title: '軽量コミュニティ',
            body: [
              '将来的には公開プロフィール、activity feed、review、collection による発見を追加できます。',
              'ただし中心は作品データベースと個人記録であり、コミュニティ機能は控えめにします。',
            ],
          },
        ],
      },
      changelog: {
        slug: 'changelog',
        title: '更新履歴',
        description: '公開ページ、API 接続、今後の機能変更を簡潔に記録します。',
        sections: [
          {
            id: 'public-pages',
            title: '公開ページ骨格',
            body: [
              'ホーム Hero、Calendar 表示、Search 表示、Search ページ、Calendar ページ、Docs 入口を作成しました。',
              'Tailwind と Radix 風のプリミティブで UI 基盤を統一し、ブラウザ標準の select を置き換えました。',
            ],
          },
          {
            id: 'api-layer',
            title: 'API 層',
            body: [
              '認証、作品、カレンダー、ライブラリ、同期、ソーシャル API の型とリクエスト層を整えました。',
              'Search はページング、ページ移動、年、クール、プラットフォーム、話数、表示方針、並び順に対応しています。',
            ],
          },
        ],
      },
    },
  },
};
