import { adminMessages } from './catalogs/admin';
import { appMessages } from './catalogs/app';
import { authMessages } from './catalogs/auth';
import { calendarMessages } from './catalogs/calendar';
import { collectionsMessages } from './catalogs/collections';
import { communityMessages } from './catalogs/community';
import { graphMessages } from './catalogs/graph';
import { homeMessages } from './catalogs/home';
import { libraryMessages } from './catalogs/library';
import { profileMessages } from './catalogs/profile';
import { reviewsMessages } from './catalogs/reviews';
import { searchMessages } from './catalogs/search';
import { subjectMessages } from './catalogs/subject';

export { locales, type Locale } from './define-messages';

export const messages = {
  'zh-CN': {
    ...adminMessages['zh-CN'],
    ...appMessages['zh-CN'],
    ...authMessages['zh-CN'],
    ...calendarMessages['zh-CN'],
    ...collectionsMessages['zh-CN'],
    ...communityMessages['zh-CN'],
    ...graphMessages['zh-CN'],
    ...homeMessages['zh-CN'],
    ...libraryMessages['zh-CN'],
    ...profileMessages['zh-CN'],
    ...reviewsMessages['zh-CN'],
    ...searchMessages['zh-CN'],
    ...subjectMessages['zh-CN'],
  },
  'en-US': {
    ...adminMessages['en-US'],
    ...appMessages['en-US'],
    ...authMessages['en-US'],
    ...calendarMessages['en-US'],
    ...collectionsMessages['en-US'],
    ...communityMessages['en-US'],
    ...graphMessages['en-US'],
    ...homeMessages['en-US'],
    ...libraryMessages['en-US'],
    ...profileMessages['en-US'],
    ...reviewsMessages['en-US'],
    ...searchMessages['en-US'],
    ...subjectMessages['en-US'],
  },
  'ja-JP': {
    ...adminMessages['ja-JP'],
    ...appMessages['ja-JP'],
    ...authMessages['ja-JP'],
    ...calendarMessages['ja-JP'],
    ...collectionsMessages['ja-JP'],
    ...communityMessages['ja-JP'],
    ...graphMessages['ja-JP'],
    ...homeMessages['ja-JP'],
    ...libraryMessages['ja-JP'],
    ...profileMessages['ja-JP'],
    ...reviewsMessages['ja-JP'],
    ...searchMessages['ja-JP'],
    ...subjectMessages['ja-JP'],
  },
} as const;

export type MessageKey = keyof (typeof messages)['zh-CN'];
