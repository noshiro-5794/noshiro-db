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
export const personalDocsSlug = 'owner';

const nav = {
  'zh-CN': [
    { slug: 'introduction', title: '关于 Noshiro DB' },
    { slug: personalDocsSlug, title: '站长小屋' },
    { slug: 'guide', title: '使用指南' },
    { slug: 'reviews', title: '文章与收藏' },
    { slug: 'community', title: '社区' },
    { slug: 'terms', title: '条款' },
    { slug: 'privacy', title: '隐私' },
    { slug: 'security', title: '安全' },
    { slug: 'status', title: '状态' },
  ],
  'en-US': [
    { slug: 'introduction', title: 'About Noshiro DB' },
    { slug: personalDocsSlug, title: "Owner's room" },
    { slug: 'guide', title: 'How to use' },
    { slug: 'reviews', title: 'Reviews and collections' },
    { slug: 'community', title: 'Community' },
    { slug: 'terms', title: 'Terms' },
    { slug: 'privacy', title: 'Privacy' },
    { slug: 'security', title: 'Security' },
    { slug: 'status', title: 'Status' },
  ],
  'ja-JP': [
    { slug: 'introduction', title: 'Noshiro DB について' },
    { slug: personalDocsSlug, title: '管理人の部屋' },
    { slug: 'guide', title: '使い方' },
    { slug: 'reviews', title: 'レビューとコレクション' },
    { slug: 'community', title: 'コミュニティ' },
    { slug: 'terms', title: '利用規約' },
    { slug: 'privacy', title: 'プライバシー' },
    { slug: 'security', title: 'セキュリティ' },
    { slug: 'status', title: 'ステータス' },
  ],
} satisfies Record<Locale, DocsContent['nav']>;

export const docsContent: Record<Locale, DocsContent> = {
  'zh-CN': {
    nav: nav['zh-CN'],
    pages: {
      introduction: {
        slug: 'introduction',
        title: '关于 Noshiro DB',
        description: '围绕动画与 Galgame 的资料库、个人记录空间和轻量社区。',
        sections: [
          {
            id: 'what',
            title: '这是什么',
            body: [
              'Noshiro DB 用来发现作品、整理作品记录、写文章、做收藏集，并通过公开内容看到其他人的兴趣轨迹。',
              '它不是论坛，也不是单纯的条目索引。这里更像一个安静的书架：作品是核心，记录和评论围绕作品生长。',
            ],
          },
          {
            id: 'tone',
            title: '网站气质',
            body: [
              '我希望它保持克制、清晰、可长期使用。界面不追求热闹，而是让信息更容易被浏览、比较、回看。',
              '未登录时可以浏览公开内容；登录后可以使用资料库、收藏集、文章、书签、通知和个人主页。',
            ],
          },
        ],
      },
      owner: {
        slug: personalDocsSlug,
        title: '站长小屋',
        description: '这里会放一些更个人的东西：我是谁、为什么做这个站、以及我想把它养成什么样。',
        sections: [
          {
            id: 'hello',
            title: '你好，我是这个网站的开发者',
            body: [
              '这一页不是公告，也不是正式文档。它更像这个网站里的一个小房间，之后我会在这里写一点关于自己的介绍。',
              'Noshiro DB 是我个人开发和维护的网站，所以我希望它不只是冷冰冰的数据库，也能留下开发者本人的一点气息。',
            ],
          },
          {
            id: 'why',
            title: '为什么会有 Noshiro DB',
            body: [
              '看过、玩过、喜欢过的作品，很容易散落在不同平台和记忆里。我想做一个可以慢慢整理它们的地方。',
              '这里将会放完整的自我介绍、开发记录、喜欢的作品、站点理念等等。',
            ],
          },
        ],
      },
      guide: {
        slug: 'guide',
        title: '使用指南',
        description: '从公开浏览到登录后的个人工作区，了解最常用的路径。',
        sections: [
          {
            id: 'public',
            title: '未登录浏览',
            body: [
              '首页展示近期放送和搜索入口。搜索可以检索作品，日历按星期展示放送条目，作品页展示详细信息。',
              '文档页说明网站定位、使用方式、隐私、安全和维护状态，方便新用户判断是否适合自己。',
            ],
          },
          {
            id: 'workspace',
            title: '登录后记录',
            body: [
              '登录后可以标记作品状态、评分、标签、进度和简评。资料库用于筛选和整理，个人主页用于展示公开资料。',
              '设置页可以管理昵称、头像、简介、语言、外观、主题色和密码相关操作。',
            ],
          },
        ],
      },
      reviews: {
        slug: 'reviews',
        title: '文章与收藏',
        description: '文章和收藏集是这个网站里最适合表达个人喜好的地方。',
        sections: [
          {
            id: 'reviews',
            title: '文章',
            body: [
              '文章使用 Markdown 编写，可以设为公开或私密，也可以标记剧透。公开文章会出现在作品页和公开个人页。',
              '我希望它更像一篇可以慢慢打磨的文字，而不是一条很快被刷走的短动态。',
            ],
          },
          {
            id: 'collections',
            title: '收藏集',
            body: [
              '收藏集用来把一组作品打包展示，比如“想推荐给朋友的作品”“某一年最喜欢的动画”或“需要重温的 Galgame”。',
              '收藏集里的条目来自自己的资料库，因此它既是展示，也是整理。',
            ],
          },
        ],
      },
      community: {
        slug: 'community',
        title: '社区',
        description: '社区功能围绕作品、文章、收藏集和用户行为展开。',
        sections: [
          {
            id: 'activity',
            title: '动态',
            body: [
              '动态页展示用户公开行为、短内容和互动。它的目标是发现人和作品，而不是制造信息噪音。',
              '你可以关注其他用户、查看公开主页、点赞、收藏、评论或举报不合适的内容。',
            ],
          },
          {
            id: 'boundaries',
            title: '边界',
            body: [
              'Noshiro DB 不计划做传统论坛、私信或复杂社交网络。社区只服务于作品发现、记录分享和文章阅读。',
              '如果之后增加更多社区能力，也会优先保证内容质量、可读性和管理可控。',
            ],
          },
        ],
      },
      terms: {
        slug: 'terms',
        title: '条款',
        description: '一些必要的使用规则，尽量简短，也尽量清楚。',
        sections: [
          {
            id: 'use',
            title: '使用规则',
            body: [
              '请不要发布违法、骚扰、恶意攻击、垃圾广告或明显破坏社区体验的内容。',
              '公开文章、收藏集、评论和动态可能被其他用户看到；发布前请确认其中没有不适合公开的信息。',
            ],
          },
          {
            id: 'moderation',
            title: '内容处理',
            body: [
              '站点会保留隐藏、锁定、删除或限制不合适内容的权利。',
              'Noshiro DB 仍是个人项目，规则会随着功能完善继续细化。',
            ],
          },
        ],
      },
      privacy: {
        slug: 'privacy',
        title: '隐私',
        description: '关于账号资料、公开内容和可见范围的说明。',
        sections: [
          {
            id: 'data',
            title: '账号数据',
            body: [
              '账号资料、头像、简介、语言、外观偏好、作品标记、标签、文章、收藏集和互动记录会用于提供网站功能。',
              '邮箱主要用于登录、验证码和账号恢复，不会在公开页面直接展示。',
            ],
          },
          {
            id: 'public',
            title: '公开内容',
            body: [
              '当你把文章、收藏集或标记设为公开时，它们可能出现在作品页、公开个人页或动态相关页面。',
              '如果不希望某些内容被别人看到，请使用私密状态，或在发布前移除敏感信息。',
            ],
          },
        ],
      },
      security: {
        slug: 'security',
        title: '安全',
        description: '关于账号保护、验证码和内容安全的说明。',
        sections: [
          {
            id: 'account',
            title: '账号安全',
            body: [
              '登录、注册和重置密码会使用邮箱验证码，并在发送验证码前进行人机验证。',
              '请使用独立密码，不要与其他重要账号共用。发现异常登录或账号问题时，可以通过 Contact 反馈。',
            ],
          },
          {
            id: 'content',
            title: '内容安全',
            body: [
              'Markdown 内容会在展示前进行安全处理，避免执行不可信内容。',
              '举报入口用于处理垃圾内容、骚扰、剧透或违法信息，管理员会根据情况审核。',
            ],
          },
        ],
      },
      status: {
        slug: 'status',
        title: '状态',
        description: '当前站点能力和维护状态。',
        sections: [
          {
            id: 'available',
            title: '已开放',
            body: [
              '公开浏览、搜索、放送日历、作品详情、登录注册、资料库、文章、收藏集、书签、通知、公开主页和动态功能已经接入。',
              '管理员同步面板、Bangumi 单条同步入口和 Subject 知识图谱也已具备基础能力。',
            ],
          },
          {
            id: 'next',
            title: '继续优化',
            body: [
              '后续会继续打磨移动端体验、文章阅读体验、社区动态质量、同步状态展示和内容管理能力。',
              '如果你遇到不可用或显示异常，可以通过 GitHub 或 Contact 告诉我。',
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
        title: 'About Noshiro DB',
        description: 'A database, personal library, and lightweight community for anime and galgames.',
        sections: [
          {
            id: 'what',
            title: 'What it is',
            body: [
              'Noshiro DB helps you discover titles, organize watch and play records, write long-form reviews, build collections, and browse public traces from other users.',
              'It is not a forum and not only an index. It is closer to a quiet shelf: titles stay at the center, while records and writing grow around them.',
            ],
          },
          {
            id: 'tone',
            title: 'Tone',
            body: [
              'The site aims to stay restrained, clear, and useful over time. The interface avoids noise so information is easier to scan, compare, and revisit.',
              'Guests can browse public content. Signed-in users get Library, Collections, Reviews, Bookmarks, Notifications, and a profile page.',
            ],
          },
        ],
      },
      owner: {
        slug: personalDocsSlug,
        title: "Owner's room",
        description: 'A more personal corner for who I am, why I built this site, and what I hope it becomes.',
        sections: [
          {
            id: 'hello',
            title: 'Hi, I build and maintain this site',
            body: [
              'This page is not an announcement or formal documentation. It is a small room inside the site where I can write something more personal later.',
              'Noshiro DB is a personal project, so I want it to keep a little trace of the person behind it, not only the shape of a database.',
            ],
          },
          {
            id: 'why',
            title: 'Why Noshiro DB exists',
            body: [
              'Works we watched, played, and loved often scatter across platforms and memory. I wanted a place where they could be slowly organized.',
              'Later, this can become a fuller self-introduction, a development note, a list of favorite works, a site manifesto, or any personal text you want visitors to read.',
            ],
          },
        ],
      },
      guide: {
        slug: 'guide',
        title: 'How to use',
        description: 'The main path from public browsing to a signed-in workspace.',
        sections: [
          {
            id: 'public',
            title: 'Browse as a guest',
            body: [
              'Home shows public Calendar and Search entry points. Search finds titles, Calendar groups airing titles by weekday, and Subject pages show details.',
              'Docs explains what the site is, how it works, and how privacy, security, terms, and status are handled.',
            ],
          },
          {
            id: 'workspace',
            title: 'Record after signing in',
            body: [
              'After signing in, you can mark status, ratings, tags, progress, and short comments. Library helps with filtering and organization, while Me presents your public profile.',
              'Settings manages nickname, avatar, bio, language, appearance, accent color, and password-related flows.',
            ],
          },
        ],
      },
      reviews: {
        slug: 'reviews',
        title: 'Reviews and collections',
        description: 'Reviews and Collections are the best places to express personal taste.',
        sections: [
          {
            id: 'reviews',
            title: 'Reviews',
            body: [
              'Reviews are written in Markdown and can be public, private, or spoiler-marked. Public reviews can appear on subject pages and public profiles.',
              'A review should feel like an article you can keep polishing, not a short post that disappears quickly.',
            ],
          },
          {
            id: 'collections',
            title: 'Collections',
            body: [
              'Collections package marked titles into visual sets, such as recommendations for a friend, favorites from a year, or galgames worth revisiting.',
              'Collection items come from your Library, so each collection is both presentation and organization.',
            ],
          },
        ],
      },
      community: {
        slug: 'community',
        title: 'Community',
        description: 'Community features revolve around subjects, reviews, collections, and activity.',
        sections: [
          {
            id: 'activity',
            title: 'Activity',
            body: [
              'Activity shows public user actions, short posts, and interactions. Its purpose is to help discover people and titles, not to create noise.',
              'You can follow users, view public profiles, like, bookmark, comment, or report inappropriate content.',
            ],
          },
          {
            id: 'boundaries',
            title: 'Boundaries',
            body: [
              'Noshiro DB does not currently aim to become a traditional forum, private messaging platform, or complex social network.',
              'Future community features will prioritize content quality, readability, and manageable moderation.',
            ],
          },
        ],
      },
      terms: {
        slug: 'terms',
        title: 'Terms',
        description: 'A short version of the rules that keep the site usable.',
        sections: [
          {
            id: 'use',
            title: 'Use',
            body: [
              'Do not post illegal content, harassment, malicious attacks, spam, or content that clearly damages the community experience.',
              'Public reviews, collections, comments, and activity may be visible to other users. Check before posting anything sensitive.',
            ],
          },
          {
            id: 'moderation',
            title: 'Moderation',
            body: [
              'The site may hide, lock, delete, or restrict content that is inappropriate or harmful.',
              'Noshiro DB is still a personal project. These rules will become more detailed as the site matures.',
            ],
          },
        ],
      },
      privacy: {
        slug: 'privacy',
        title: 'Privacy',
        description: 'How account data and public content are treated.',
        sections: [
          {
            id: 'data',
            title: 'Account data',
            body: [
              'Profile, avatar, bio, language, appearance, marks, tags, reviews, collections, and interactions are used to provide site features.',
              'Email is primarily used for login, verification codes, and account recovery. It is not shown directly on public pages.',
            ],
          },
          {
            id: 'public',
            title: 'Public content',
            body: [
              'When you make reviews, collections, or marks public, they may appear on subject pages, public profiles, or activity-related pages.',
              'Use private status or remove sensitive details before publishing anything you do not want others to see.',
            ],
          },
        ],
      },
      security: {
        slug: 'security',
        title: 'Security',
        description: 'Notes on account security, verification, and content safety.',
        sections: [
          {
            id: 'account',
            title: 'Account security',
            body: [
              'Login, registration, and password reset use email verification codes, with human verification before sending codes.',
              'Use a unique password. If you notice account issues, contact the maintainer through Contact.',
            ],
          },
          {
            id: 'content',
            title: 'Content safety',
            body: [
              'Markdown content is sanitized before display so untrusted content is not executed directly.',
              'Reports help handle spam, harassment, spoilers, and illegal content. Admins review reports as needed.',
            ],
          },
        ],
      },
      status: {
        slug: 'status',
        title: 'Status',
        description: 'Current site capabilities and maintenance state.',
        sections: [
          {
            id: 'available',
            title: 'Available',
            body: [
              'Public browsing, search, calendar, subject pages, auth, Library, Reviews, Collections, Bookmarks, Notifications, public profiles, and Activity are wired.',
              'Admin sync panel, Bangumi single-subject sync entry, and Subject knowledge graph are also available at a basic level.',
            ],
          },
          {
            id: 'next',
            title: 'Next improvements',
            body: [
              'Future work will keep improving mobile polish, review reading, activity quality, sync status visibility, and moderation tooling.',
              'If something breaks or renders poorly, use GitHub or Contact at the bottom of the page.',
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
        title: 'Noshiro DB について',
        description: 'アニメとギャルゲームのためのデータベース、個人ライブラリ、軽量コミュニティです。',
        sections: [
          {
            id: 'what',
            title: 'このサイトについて',
            body: [
              'Noshiro DB は作品を見つけ、視聴・プレイ記録を整理し、長いレビューを書き、コレクションを作り、他のユーザーの公開記録を見るための場所です。',
              'フォーラムでも単なる索引でもありません。作品を中心に、記録と文章がその周りに積み重なる静かな棚のようなサイトを目指しています。',
            ],
          },
          {
            id: 'tone',
            title: '雰囲気',
            body: [
              '長く使えるように、控えめで読みやすい画面を大切にします。情報を探し、比べ、後から読み返しやすいことを優先します。',
              '未ログインでも公開内容を閲覧できます。ログイン後は Library、Collections、Reviews、Bookmarks、通知、プロフィールページを利用できます。',
            ],
          },
        ],
      },
      owner: {
        slug: personalDocsSlug,
        title: '管理人の部屋',
        description: '管理人自身のこと、Noshiro DB を作った理由、これから書き足したい個人的な話のための場所です。',
        sections: [
          {
            id: 'hello',
            title: 'このサイトを作っている人について',
            body: [
              'このページはお知らせでも正式なドキュメントでもありません。あとで管理人自身の紹介を書ける、小さな部屋のような場所です。',
              'Noshiro DB は個人で開発しているサイトなので、データベースらしさだけでなく、作っている人の気配も少し残したいと思っています。',
            ],
          },
          {
            id: 'why',
            title: 'Noshiro DB を作った理由',
            body: [
              '見た作品、遊んだ作品、好きだった作品は、いろいろな場所と記憶の中に散らばりがちです。それらをゆっくり整理できる場所がほしいと思いました。',
              'ここには今後、自己紹介、開発メモ、好きな作品、サイトの考え方など、訪問者に読んでほしい個人的な文章を置けます。',
            ],
          },
        ],
      },
      guide: {
        slug: 'guide',
        title: '使い方',
        description: '公開ページの閲覧からログイン後のワークスペースまで、基本的な流れを説明します。',
        sections: [
          {
            id: 'public',
            title: '未ログインで見る',
            body: [
              'Home には Calendar と Search の入口があります。Search で作品を探し、Calendar で曜日ごとの放送作品を見て、Subject で詳細を確認できます。',
              'Docs ではサイトの目的、使い方、プライバシー、安全、状態を確認できます。',
            ],
          },
          {
            id: 'workspace',
            title: 'ログイン後に記録する',
            body: [
              'ログイン後は状態、評価、タグ、進捗、短いコメントを記録できます。Library は整理、Me は公開プロフィールの表示に使います。',
              'Settings ではニックネーム、アバター、自己紹介、言語、外観、アクセントカラー、パスワード関連を管理できます。',
            ],
          },
        ],
      },
      reviews: {
        slug: 'reviews',
        title: 'レビューとコレクション',
        description: 'Review と Collection は、好みや視点を表現しやすい場所です。',
        sections: [
          {
            id: 'reviews',
            title: 'Review',
            body: [
              'Review は Markdown で書けます。公開、非公開、ネタバレを設定でき、公開 Review は作品ページや公開プロフィールに表示されます。',
              'Review はすぐ流れていく短文ではなく、少しずつ整えられる文章として扱いたいと考えています。',
            ],
          },
          {
            id: 'collections',
            title: 'Collection',
            body: [
              'Collection は記録した作品を視覚的なセットにまとめる機能です。友人に勧めたい作品、ある年のお気に入り、もう一度触れたい作品などに使えます。',
              '項目は自分の Library から追加するため、Collection は見せるための場所であり、整理するための場所でもあります。',
            ],
          },
        ],
      },
      community: {
        slug: 'community',
        title: 'コミュニティ',
        description: 'コミュニティ機能は作品、Review、Collection、ユーザー行動を中心にしています。',
        sections: [
          {
            id: 'activity',
            title: 'Activity',
            body: [
              'Activity では公開された行動、短い投稿、やり取りを表示します。人と作品を見つけるための場所であり、ノイズを増やすための場所ではありません。',
              'ユーザーをフォローし、公開プロフィールを見て、いいね、ブックマーク、コメント、通報ができます。',
            ],
          },
          {
            id: 'boundaries',
            title: '境界',
            body: [
              'Noshiro DB は現時点で、従来型フォーラム、DM、複雑な SNS になることを目指していません。',
              '今後コミュニティ機能を増やす場合も、内容の質、読みやすさ、管理しやすさを優先します。',
            ],
          },
        ],
      },
      terms: {
        slug: 'terms',
        title: '利用規約',
        description: 'Noshiro DB を利用する際の基本ルールです。',
        sections: [
          {
            id: 'use',
            title: '利用ルール',
            body: [
              '違法コンテンツ、嫌がらせ、悪意ある攻撃、スパム、コミュニティ体験を明確に損なう内容を投稿しないでください。',
              '公開 Review、Collection、コメント、Activity は他のユーザーに見える可能性があります。公開前に内容を確認してください。',
            ],
          },
          {
            id: 'moderation',
            title: 'モデレーション',
            body: [
              '不適切または有害な内容は、非表示、ロック、削除、制限される場合があります。',
              'Noshiro DB は個人プロジェクトとして運用中です。機能の成熟に合わせてルールも更新されます。',
            ],
          },
        ],
      },
      privacy: {
        slug: 'privacy',
        title: 'プライバシー',
        description: 'アカウントデータと公開コンテンツの扱いについて。',
        sections: [
          {
            id: 'data',
            title: 'アカウントデータ',
            body: [
              'プロフィール、アバター、自己紹介、言語、外観、記録、タグ、レビュー、コレクション、インタラクションはサイト機能の提供に使われます。',
              'メールアドレスは主にログイン、認証コード、アカウント復旧に使われ、公開ページには直接表示されません。',
            ],
          },
          {
            id: 'public',
            title: '公開コンテンツ',
            body: [
              'Review、Collection、記録を公開にすると、作品ページ、公開プロフィール、Activity 関連ページに表示される場合があります。',
              '見られたくない情報は非公開にするか、公開前に削除してください。',
            ],
          },
        ],
      },
      security: {
        slug: 'security',
        title: 'セキュリティ',
        description: 'アカウント保護、認証、コンテンツ安全性について。',
        sections: [
          {
            id: 'account',
            title: 'アカウント保護',
            body: [
              'ログイン、登録、パスワードリセットではメール認証コードを使い、コード送信前に人間確認を行います。',
              '他の重要なアカウントと同じパスワードは使わないでください。問題があれば Contact から連絡してください。',
            ],
          },
          {
            id: 'content',
            title: 'コンテンツ安全性',
            body: [
              'Markdown は表示前に安全処理され、不信頼な内容が直接実行されないようにします。',
              '通報機能はスパム、嫌がらせ、ネタバレ、違法コンテンツの対応に使われ、必要に応じて管理者が確認します。',
            ],
          },
        ],
      },
      status: {
        slug: 'status',
        title: 'ステータス',
        description: '現在利用できる機能とメンテナンス状態です。',
        sections: [
          {
            id: 'available',
            title: '利用可能',
            body: [
              '公開閲覧、検索、カレンダー、作品詳細、認証、Library、Reviews、Collections、Bookmarks、通知、公開プロフィール、Activity が接続されています。',
              'Admin 同期パネル、Bangumi 単体同期入口、Subject 知識グラフも基本機能を備えています。',
            ],
          },
          {
            id: 'next',
            title: '今後の改善',
            body: [
              'モバイル表示、Review の読み心地、Activity の質、同期状態表示、モデレーション機能を引き続き改善します。',
              '表示崩れや不具合があれば、ページ下部の GitHub または Contact から知らせてください。',
            ],
          },
        ],
      },
    },
  },
};
