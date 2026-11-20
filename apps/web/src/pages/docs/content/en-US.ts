import type { DocsPages } from './types';

export const enUSPages = {
  introduction: {
    title: 'About Noshiro DB',
    description: 'A knowledge base, personal library, and community for anime, manga, games, and related media.',
    sections: [
      {
        id: 'what',
        title: 'Explore the catalogue',
        body: [
          'Browse works, characters, creators, releases, and their connections across anime, manga, games, and related media.',
          'Curated collections currently focus on anime and visual novels. The calendar covers anime airings, and linked records reflect the sources available for each entity.',
        ],
      },
      {
        id: 'tone',
        title: 'Build a personal library',
        body: [
          'Sign in to track status, progress, ratings, and tags. Write reviews, organize collections, and share public records with the community.',
        ],
      },
    ],
  },
  owner: {
    title: "Owner's room",
    description: 'A personal note from the developer and maintainer of Noshiro DB.',
    sections: [
      {
        id: 'hello',
        title: 'Hi, I build and maintain this site',
        body: ['I build and maintain Noshiro DB as an independent project.'],
      },
      {
        id: 'why',
        title: 'Why Noshiro DB exists',
        body: [
          'The works I watch, read, and play often end up scattered across platforms. I wanted one place to keep those records and explore how the works are connected.',
        ],
      },
    ],
  },
  guide: {
    title: 'How to use',
    description: 'Find works, follow their connections, and record your progress.',
    sections: [
      {
        id: 'public',
        title: 'Browse as a guest',
        body: [
          'Search for a title or check the anime airing calendar. Open a work page for its synopsis, credits, and linked entries.',
        ],
      },
      {
        id: 'workspace',
        title: 'Record after signing in',
        body: [
          'Sign in to record your progress, ratings, tags, and short comments. Use Library to organize your entries and Settings to manage your profile and preferences.',
        ],
      },
    ],
  },
  reviews: {
    title: 'Reviews and collections',
    description: 'Write about individual works and group entries from your library.',
    sections: [
      {
        id: 'reviews',
        title: 'Reviews',
        body: [
          'Write reviews in Markdown. Choose public or private visibility and mark spoilers where needed. Public reviews can appear on work pages and profiles.',
        ],
      },
      {
        id: 'collections',
        title: 'Collections',
        body: [
          'Add works from your Library to a collection, such as a reading list, a series retrospective, or recommendations to share.',
        ],
      },
    ],
  },
  community: {
    title: 'Community',
    description: 'Discover works and people through shared records, reviews, and collections.',
    sections: [
      {
        id: 'activity',
        title: 'Activity',
        body: [
          'Browse public activity and profiles. Sign in to follow users, like, bookmark, comment, or report content.',
        ],
      },
      {
        id: 'boundaries',
        title: 'Visibility and reporting',
        body: [
          'Check the visibility of your entries before sharing them. Use the report action on the relevant item when it needs moderation.',
        ],
      },
    ],
  },
  terms: {
    title: 'Terms',
    description: 'The rules for publishing and interacting on Noshiro DB.',
    sections: [
      {
        id: 'use',
        title: 'Use',
        body: [
          'Keep posts and interactions lawful and respectful. Harassment, malicious attacks, and spam are prohibited.',
          'Before publishing a review, collection, comment, or activity post, check for information you want to keep private.',
        ],
      },
      {
        id: 'moderation',
        title: 'Moderation',
        body: [
          'The site may hide, lock, remove, or restrict inappropriate or harmful content. These rules may be updated as the service develops.',
        ],
      },
    ],
  },
  privacy: {
    title: 'Privacy',
    description: 'How Noshiro DB uses account information and displays public content.',
    sections: [
      {
        id: 'data',
        title: 'Account data',
        body: [
          'Your profile, preferences, library records, and interactions support the features you use. Your email address is used for sign-in, verification, and account recovery. It stays off public pages.',
        ],
      },
      {
        id: 'public',
        title: 'Public content',
        body: [
          'Public reviews, collections, and library entries may appear on work pages, profiles, and activity feeds. Choose private visibility for records you want to keep to yourself.',
        ],
      },
    ],
  },
  security: {
    title: 'Security',
    description: 'Account protection, safe content display, and reporting.',
    sections: [
      {
        id: 'account',
        title: 'Account security',
        body: [
          'Sign in with your password or an available verification method. Registration and password recovery use email codes and may require a CAPTCHA before a code is sent.',
          'Use a unique password. If you notice unusual account activity, use the Contact link in the footer.',
        ],
      },
      {
        id: 'content',
        title: 'Content safety',
        body: [
          'Markdown is sanitized before it is displayed. You can report spam, harassment, spoilers, or illegal content for moderation.',
        ],
      },
    ],
  },
  status: {
    title: 'Status',
    description: 'Available features and where to report a problem.',
    sections: [
      {
        id: 'available',
        title: 'Available features',
        body: [
          'Browse the catalogue, search by title, check the anime calendar, and follow work relationships. With an account, you can use Library, reviews, collections, bookmarks, notifications, and community activity.',
        ],
      },
      {
        id: 'next',
        title: 'Report a problem',
        body: [
          'Use the GitHub or Contact link in the footer to report an issue. Include the affected page and the steps that led to the problem.',
        ],
      },
    ],
  },
} satisfies DocsPages;
