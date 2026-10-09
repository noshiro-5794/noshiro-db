import { defineMessages } from '../define-messages';

/**
 * Copy for the visitor-facing site: the public top bar and the landing page.
 *
 * This is the one place where the wording is written for people who have never
 * seen the app. It describes what a visitor gets — finding a work, following
 * the season, keeping a list — and stays away from how the catalogue is built.
 */
export const publicMessages = defineMessages({
  'zh-CN': {
    'public.openMenu': '打开菜单',
    'public.closeMenu': '关闭菜单',
    'public.menuBrowse': '浏览',

    'public.heroChip': '无需注册即可浏览',
    'public.heroTitle': '动画与 Galgame 的开放资料库',
    'public.heroBody':
      '搜日语、中文或英文标题，都能落到同一部作品；查看当季放送时间、简介与制作阵容；把在看、想看、看完的作品整理成自己的清单。',
    'public.startSearch': '搜索作品',
    'public.viewSchedule': '查看放送表',

    'public.seasonHeading': '本季放送',
    'public.searchBody': '按标题、类型或年份筛选，从作品库里找到想看的那一部。',
    'public.searchPlaceholder': '搜索标题',
    'public.searchEmpty': '暂无可展示的作品条目。',
    'public.more': '查看更多',
  },
  'en-US': {
    'public.openMenu': 'Open menu',
    'public.closeMenu': 'Close menu',
    'public.menuBrowse': 'Browse',

    'public.heroChip': 'No account needed to browse',
    'public.heroTitle': 'An open catalogue of anime and visual novels',
    'public.heroBody':
      'Search in Japanese, Chinese or English and land on the same work. Follow the season schedule, read synopses and staff credits, and keep everything you watch in one list.',
    'public.startSearch': 'Search the catalogue',
    'public.viewSchedule': 'See the weekly schedule',

    'public.seasonHeading': 'Airing this season',
    'public.searchBody': 'Filter by title, type or year to find what to watch next.',
    'public.searchPlaceholder': 'Search titles',
    'public.searchEmpty': 'No works are ready to display yet.',
    'public.more': 'View more',
  },
  'ja-JP': {
    'public.openMenu': 'メニューを開く',
    'public.closeMenu': 'メニューを閉じる',
    'public.menuBrowse': 'メニュー',

    'public.heroChip': '登録なしで閲覧できます',
    'public.heroTitle': 'アニメとギャルゲーのオープンなデータベース',
    'public.heroBody':
      '日本語・中国語・英語、どのタイトルで検索しても同じ作品にたどり着きます。今期の放送時間やあらすじ、スタッフ情報を確認して、観た作品をひとつのリストにまとめましょう。',
    'public.startSearch': '作品を検索',
    'public.viewSchedule': '放送スケジュールを見る',

    'public.seasonHeading': '今期の放送',
    'public.searchBody': 'タイトル・種別・年で絞り込み、次に観たい作品を見つけましょう。',
    'public.searchPlaceholder': 'タイトルを検索',
    'public.searchEmpty': '表示できる作品がまだありません。',
    'public.more': 'もっと見る',
  },
});
