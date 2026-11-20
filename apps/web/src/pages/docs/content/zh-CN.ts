import type { DocsPages } from './types';

export const zhCNPages = {
  introduction: {
    title: '关于 Noshiro DB',
    description: '二次元作品与关联知识库，兼具个人资料库与社区。',
    sections: [
      {
        id: 'what',
        title: '浏览作品和关联知识',
        body: [
          'Noshiro DB 汇集动画、漫画、游戏等作品及其关联资料。你可以浏览作品、角色、创作者、发行版本和它们之间的关系。',
          '目前精选目录主要覆盖动画与视觉小说，放送日历展示动画排期。关联条目的覆盖范围由可用来源决定。',
        ],
      },
      {
        id: 'tone',
        title: '整理个人资料库',
        body: ['注册后可以记录作品状态、进度、评分和标签，也可以写评论、整理收藏集，和其他用户分享公开记录。'],
      },
    ],
  },
  owner: {
    title: '站长小屋',
    description: 'Noshiro DB 开发者兼维护者的个人随笔。',
    sections: [
      {
        id: 'hello',
        title: '你好，我是这个网站的开发者',
        body: ['Noshiro DB 是我独立开发和维护的项目。'],
      },
      {
        id: 'why',
        title: '为什么会有 Noshiro DB',
        body: [
          '看过、读过、玩过的作品很容易散落在不同平台。我想有一个地方整理这些记录，也能顺着作品之间的关系继续探索。',
        ],
      },
    ],
  },
  guide: {
    title: '使用指南',
    description: '查找作品、浏览关联资料，并记录你的进度。',
    sections: [
      {
        id: 'public',
        title: '未登录浏览',
        body: ['用标题搜索作品，或在放送日历查看动画排期。打开作品页可以浏览简介、制作人员和关联条目。'],
      },
      {
        id: 'workspace',
        title: '登录后记录',
        body: ['登录后可以记录进度、评分、标签和简评。在资料库整理条目，在设置中管理个人资料和使用偏好。'],
      },
    ],
  },
  reviews: {
    title: '文章与收藏',
    description: '为作品撰写文章，将资料库中的条目整理成收藏集。',
    sections: [
      {
        id: 'reviews',
        title: '文章',
        body: ['使用 Markdown 撰写文章，选择公开或私密，并按需标记剧透。公开文章可出现在作品页和个人主页。'],
      },
      {
        id: 'collections',
        title: '收藏集',
        body: ['从资料库选择作品，整理为阅读计划、系列回顾，或一份可以分享的推荐清单。'],
      },
    ],
  },
  community: {
    title: '社区',
    description: '通过公开记录、文章和收藏集发现作品与其他用户。',
    sections: [
      {
        id: 'activity',
        title: '动态',
        body: ['浏览公开动态和个人主页。登录后可以关注用户、点赞、收藏、评论或举报。'],
      },
      {
        id: 'boundaries',
        title: '公开范围与举报',
        body: ['分享前请检查条目的可见范围。需要管理者介入时，可以直接举报相关内容。'],
      },
    ],
  },
  terms: {
    title: '条款',
    description: '在 Noshiro DB 发布内容和参与互动的基本规则。',
    sections: [
      {
        id: 'use',
        title: '使用规则',
        body: [
          '请遵守法律并尊重其他用户。禁止骚扰、恶意攻击和垃圾广告。',
          '发布文章、收藏集、评论或动态前，请检查其中是否含有希望保密的信息。',
        ],
      },
      {
        id: 'moderation',
        title: '内容处理',
        body: ['站点可以隐藏、锁定、删除或限制不当或有害的内容。使用规则会随功能和运营需要更新。'],
      },
    ],
  },
  privacy: {
    title: '隐私',
    description: 'Noshiro DB 如何使用账号信息和展示公开内容。',
    sections: [
      {
        id: 'data',
        title: '账号数据',
        body: [
          '个人资料、使用偏好、资料库记录和互动记录用于提供站点功能。邮箱用于登录、验证和账号恢复，公开页面不会显示邮箱。',
        ],
      },
      {
        id: 'public',
        title: '公开内容',
        body: ['公开的文章、收藏集和作品记录可能出现在作品页、个人主页或动态中。仅供自己查看的记录可以设为私密。'],
      },
    ],
  },
  security: {
    title: '安全',
    description: '关于账号保护、内容展示和举报的说明。',
    sections: [
      {
        id: 'account',
        title: '账号安全',
        body: [
          '登录可使用密码或站点提供的验证方式。注册和找回密码使用邮件验证码，发送前可能需要完成人机验证。',
          '请为本站使用独立密码。发现账号异常时，可通过页脚的联系入口反馈。',
        ],
      },
      {
        id: 'content',
        title: '内容安全',
        body: ['Markdown 内容会在展示前进行安全处理。垃圾内容、骚扰、剧透或违法信息可以通过举报入口提交审核。'],
      },
    ],
  },
  status: {
    title: '状态',
    description: '目前开放的功能与问题反馈渠道。',
    sections: [
      {
        id: 'available',
        title: '已开放的功能',
        body: [
          '访客可以浏览目录、按标题搜索、查看动画排期和作品关系。登录后可使用资料库、文章、收藏集、书签、通知和社区动态。',
        ],
      },
      {
        id: 'next',
        title: '反馈问题',
        body: ['可通过页脚的 GitHub 或联系入口反馈问题。请附上受影响的页面和遇到问题时的操作步骤。'],
      },
    ],
  },
} satisfies DocsPages;
