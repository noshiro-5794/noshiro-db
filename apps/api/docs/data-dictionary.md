# Noshiro DB 数据字典

这份字典覆盖 Alembic `0022_scope_taxonomy_aliases` 的 104 张应用表。表名省略 `public.` 前缀。`ingest` 和 `ranking` 表标注了完整名称。末尾列出 `0009` 独有的旧表和视图，方便对照迁移。

每行示例只展示该表的关键字段。《葬送的芙莉莲 第二季》的 Bangumi 515759、AniList 182255 和日文展示版本取自本地预览。其他示例用于说明结构，主键和引用中的短名称是示意值。账户、验证、令牌及会话示例均使用虚构信息。

## 采集、来源版本与映射

| 表 | 数据与用途 | 示例 |
| --- | --- | --- |
| `provider` | 来源注册、启用状态，以及存储、公开展示和 AI 使用策略。 | `slug=bangumi, ai_usage_policy=unknown, is_enabled=true` |
| `provider_namespace` | 一个来源内的资源命名空间。不同资源类型可以有相同外部 ID。 | `provider_id=Bangumi, slug=subject, resource_type=subject` |
| `provider_record` | 外部资源的稳定身份、URL、抓取状态和最新版本。 | `namespace_id=Bangumi subject, external_id=515759, status=active` |
| `provider_revision` | 一个来源条目解析后的 JSON 快照、哈希和抓取时间。 | `record_id=Bangumi 515759, payload={"id":515759,"type":2}`，仅列出部分键 |
| `ingest.source_document` | 存储策略允许时归档 HTTP 原始响应字节，按来源和哈希去重。 | `provider_id=Bangumi, body_hash=<sha256>, body=<response bytes>` |
| `ingest.source_fetch` | 一次 HTTP 响应的端点、方法、状态、时间和文档引用。 | `endpoint=/v0/subjects/515759, method=GET, status_code=200` |
| `ingest.source_batch` | 将一次同步中的主体响应和后续分页归到同一批次，记录完成时间。 | `provider_id=Bangumi, external_id=515759, completed_at=2026-11-24T04:00:00Z` |
| `ingest.revision_source` | 连接解析版本和原始抓取，JSON Pointer 指明响应中的片段。 | `revision_id=AniList 182255 的版本, fetch_id=抓取 UUID, json_pointer=/data/Media` |
| `mapping_run` | 来源版本用哪个映射器及版本处理，记录状态、耗时和错误。 | `mapper=bangumi.subject, mapper_version=bangumi-subject-v5, status=succeeded` |
| `provider_observation` | 一次结构化观测的身份、结构版本、内容哈希和可选投影 JSON。 | `schema_name=index.work, normalized_data={"_projection_hash":"<sha256>"}` |
| `provider_current_observation` | 为来源条目和映射器指向当前可用观测。 | `provider_record_id=Bangumi 515759, mapper=bangumi.subject, observation_id=观测 UUID` |

## 实体、事实与作品关系

| 表 | 数据与用途 | 示例 |
| --- | --- | --- |
| `entity` | 目录对象共用的 UUID、类型、生命周期、可见性、受众及剧透等级。 | `id=88d4dfac-c121-46fc-9d27-4ab29dbe2efd, kind=work, lifecycle=active` |
| `work` | 作品子类型，与实体主键共用 UUID。 | `entity_id=芙莉莲第二季, work_type=anime` |
| `anime_profile` | 动画形式、原作类型、集数和首末播日期。日历及匹配仍在读取。 | `work_id=芙莉莲第二季, format=TV, episode_count=10` |
| `entity_representation` | 一个来源记录对某个实体的表示方式、匹配方法和置信度。 | `provider_record_id=Bangumi 515759, entity_id=来源作品 UUID, mapping_kind=exact` |
| `entity_identity_membership` | 记录两个实体的归并方向、是否生效和对应归并事件。 | `source_entity_id=来源作品 UUID, target_entity_id=规范作品 UUID, is_active=true` |
| `entity_merge_event` | 一次归并操作的依据、当时状态及撤销记录。 | `method=rule, reason=已核对同一季, source_entity_id=来源作品 UUID` |
| `entity_split_event` | 一次拆分的理由、关联归并事件及恢复状态。 | `merge_event_id=归并事件 UUID, reason=两条记录对应不同季度` |
| `entity_name` | 原题、正式译名和别名，带语言、原名标记及来源。 | `text=葬送のフリーレン 第2期, language=ja, is_original=true` |
| `entity_description` | 来源或编辑资料的简介原文，以及语言、安全和剧透信息。 | `text=一段日文简介, language=ja, provider_record_id=来源条目 UUID` |
| `predicate` | 事实字段定义，包括稳定标识、显示名称和声明类型。 | `slug=episode-count, name=Episode Count, value_type=number` |
| `fact` | 实体的通用属性值，同一属性可以有多个来源支持或多个候选值。 | `entity_id=芙莉莲第二季, predicate_id=episode-count, value=10` |
| `fact_evidence` | 某个事实的观测证据及其值在来源中的位置。 | `fact_id=集数事实 UUID, observation_id=AniList 观测 UUID, json_pointer=/episodes` |
| `resolution_decision` | 对一个实体、字段和语言的当前事实选择与变化历史。 | `predicate_id=episode-count, selected_fact_id=集数事实 UUID, is_active=true` |
| `entity_relation` | 目录实体间的类型化边及额外条件，例如续作或同季关系。 | `from_entity_id=第一季, to_entity_id=第二季, relation_type=sequel` |
| `entity_relation_evidence` | 关系的来源观测、原始关系值及 JSON 路径。 | `relation_id=续作关系 UUID, raw_relation=SEQUEL, observation_id=来源观测 UUID` |
| `contributor` | 将目录实体标记为可承担职员、组织或配音关系的贡献者。 | `entity_id=北川朋哉, kind=person` |
| `person` | 人物子类型，通过贡献者主键关联实体和名称。 | `contributor_id=北川朋哉的贡献者 UUID` |
| `organization` | 组织子类型，通过贡献者主键关联实体和名称。 | `contributor_id=MADHOUSE 的贡献者 UUID` |
| `credit` | 作品、贡献者、职务和原始署名，带来源观测。 | `work_id=芙莉莲第二季, contributor_id=北川朋哉, role=Director` |
| `appearance` | 角色在作品中的出场关系、角色定位及剧透等级。 | `work_id=芙莉莲第二季, character_entity_id=芙莉莲, role=main` |
| `voice_performance` | 一项角色出场所对应的配音贡献者、语言和署名。 | `appearance_id=芙莉莲的出场记录, contributor_id=種﨑敦美, language=ja` |
| `release` | 一个发行版本的日期与精度、地区、平台及版本类型。 | `release_type=edition, date_start=2004-04-28, date_precision=day, platform=Windows` |
| `release_work` | 发行版本和所含作品之间的关系。 | `release_id=PC 版, work_id=CLANNAD, role=main` |
| `release_work_evidence` | 版本与作品关系的来源观测、路径和原始角色类型。 | `release_work_id=PC 版关联, json_pointer=/vns/0, observation_id=VNDB 观测` |
| `media_asset` | 图片等媒体资源的 URL、尺寸、来源和安全等级。 | `url=https://example.test/poster.webp, media_type=image, safety=safe` |
| `entity_media` | 选择某个资源作为作品海报、截图等用途，附排序及观测。 | `entity_id=芙莉莲第二季, asset_id=海报 UUID, purpose=poster, sort_order=0` |
| `external_link` | 作品外部链接、名称及来源证据。 | `url=https://frieren-anime.jp/, label=Official website, link_type=official` |
| `content_rating` | 分级制度、地区、分级值及最低年龄。 | `system=ESRB, value=T, region=US, minimum_age=13` |
| `curated_collection` | 站方维护的目录分类入口，例如动画和视觉小说。 | `slug=anime, name=Anime, is_enabled=true` |
| `curated_membership` | 实体加入站方目录的依据及列表状态。 | `collection_id=动画目录, entity_id=芙莉莲第二季, listing_state=listed` |

## 术语与分类

| 表 | 数据与用途 | 示例 |
| --- | --- | --- |
| `taxonomy_alias` | 已审核的文本异写到规范术语的对应，按词表、来源范围和语言限定。 | `vocabulary=provider-tag, source_text=SF, normalized_key=sf, term_id=科幻, is_reviewed=true` |
| `taxonomy` | 保存一套有明确语义的术语体系，供术语所属域使用。 | `slug=vndb-tag, name=VNDB tags` |
| `taxonomy_term` | 术语体系中的稳定术语及可选上级。 | `taxonomy_id=VNDB 术语体系, slug=example-term` |
| `taxonomy_term_label` | 同一术语的多语言、多文字标签和首选标记。 | `term_id=示例术语, language=ja, text=サンプル, is_preferred=true` |
| `taxonomy_term_mapping` | 来源术语记录与目录术语之间的 ID 映射和置信度。 | `provider_record_id=VNDB 术语来源记录, term_id=目录术语, confidence=1` |
| `entity_term` | 实体关联术语的结构化证据、相关度和剧透等级。 | `entity_id=示例视觉小说, term_id=来源术语, relevance=2.3, spoiler_level=2` |

## 归并候选、AI 与展示发布

| 表 | 数据与用途 | 示例 |
| --- | --- | --- |
| `match_candidate` | 一对可能是同一实体的候选、相似度、候选差距、冲突和状态。 | `left_entity_id=Bangumi 作品, right_entity_id=AniList 作品, status=pending` |
| `match_evidence` | 支持或反对归并的证据、观测和权重。 | `candidate_id=候选 UUID, evidence_type=provider_search, weight=0.98` |
| `candidate_decision` | 候选的接受、分组、拒绝或弃权记录，带执行者和理由。 | `candidate_id=候选 UUID, outcome=bind, reason=来源 ID 和季度一致` |
| `agent_session` | 用户与 Agent 的持久会话容器。 | `user_id=示例用户, title=作品资料查询, is_active=true` |
| `agent_run` | 一次 Agent 执行的状态、预算、恢复断点和幂等键。 | `title=动画元数据整理, status=succeeded, idempotency_scope=示例任务` |
| `agent_message` | Agent 运行中的消息、角色、顺序和工具调用。 | `run_id=示例运行, sequence=1, role=user, content=查询一部动画` |
| `agent_step` | 一次运行中的操作步骤、输入输出、耗时、费用和重试次数。 | `run_id=示例运行, skill_name=metadata_draft, status=succeeded` |
| `tool_invocation` | 工具执行的参数、权限、结果、状态、耗时和幂等性。 | `step_id=示例步骤, tool_name=get_metadata_evidence, status=succeeded` |
| `source_artifact` | Agent 取得的外部证据材料、对象地址、哈希、许可和保留期限。 | `source_url=https://example.test/evidence, mime_type=text/html, content_hash=<sha256>` |
| `ai_run` | 单次模型推理的提供商、模型、用途、令牌、费用及结果。 | `use_case=metadata_draft, model=示例模型, input_tokens=900, output_tokens=310` |
| `ai_proposal` | 模型给出的归并等业务提议、置信度、审查状态和目标。 | `proposal_type=entity_match, match_candidate_id=候选 UUID, confidence=0.98` |
| `ai_claim` | Agent 在某个步骤提出的单条结构化主张、置信度和策略结果。 | `predicate_slug=normalized-term, target_entity_id=示例作品, proposed_value=Windows` |
| `claim_evidence` | 单条主张引用的观测或材料、定位及证据摘要哈希。 | `claim_id=主张 UUID, observation_id=观测 UUID, locator=/platform` |
| `ai_policy` | 一个 AI 用例的自动执行门槛、评估要求及影子模式。 | `use_case=entity_match, shadow_mode=true, minimum_score=0.9950` |
| `ai_evaluation_run` | 某版策略在指定评估集上的精确率、召回率及通过状态。 | `dataset_version=sample-v1, sample_count=200, precision=0.995, passed=true` |
| `approval_request` | 需要人批准的操作、风险、差异、审批状态、期限和参与人。 | `status=pending, summary=审核同一作品归并, run_id=示例运行` |
| `entity_metadata_revision` | 某作品和语言的标题、Markdown 简介、封面选择、输入指纹及审核状态。 | `id=3, language=ja, title_text=葬送のフリーレン 第2期, state=approved` |
| `entity_metadata_citation` | 展示简介引用的来源简介、顺序及引用内容哈希。 | `revision_id=3, position=1, description_id=3, evidence_hash=<sha256>` |
| `entity_metadata_field_choice` | 展示字段的规范键、标签、顺序和证据指针。 | `revision_id=3, field_key=infobox:director, label=監督, position=3` |
| `entity_metadata_publication` | 每个作品和语言当前公开的审核版本。 | `entity_id=芙莉莲第二季, language=ja, revision_id=3` |

## 日历、排序与同步

| 表 | 数据与用途 | 示例 |
| --- | --- | --- |
| `airing_event` | 从来源观测到的播出时间、星期、时区、地区和精度。 | `work_id=示例动画, starts_at=2026-01-16T14:00:00Z, timezone=Asia/Tokyo` |
| `airing_board` | 某季度有效或历史播出表的批次、范围及来源观测。 | `season_key=2026Q1, status=active, item_count=120` |
| `airing_board_entry` | 播出表中的作品或单集行、采用的时间和来源证据。 | `board_id=2026Q1 的板, work_id=示例动画, episode_number=1, precision=minute` |
| `ranking.provider_metric` | 来源评分、票数、收藏量等内部时间序列。 | `provider_record_id=来源条目 UUID, metric=votes, value=2000` |
| `ranking.entity_rank` | 作品面向站内排序的派生分数及刷新时间。 | `entity_id=示例动画, score=82.421000, refreshed_at=2026-11-24T04:00:00Z` |
| `sync_state` | 周期增量任务的游标、分片、终点和失败计数。 | `task_name=incremental_subject, shard=main, current_id=515759, status=running` |
| `sync_error` | 单条记录的同步错误和重试次数。 | `task_name=incremental_subject, entity_id=515759, retry_count=2` |
| `sync_job` | 一次显式导入任务的状态、进度、队列身份、租约和结果。 | `job_type=bangumi_subject, status=succeeded, processed_count=1` |
| `sync_campaign` | 批量同步任务的来源、阶段、配置、计数、租约和费用。 | `provider_slug=anilist, campaign_type=full, ai_mode=off, processed_items=200` |
| `sync_work_item` | 批量任务的单条来源工作项、游标、结果、重试和 AI 阶段进度。 | `campaign_id=示例任务, cursor=182255, status=succeeded, attempt=1` |
| `alembic_version` | 标记数据库已应用的 Alembic 迁移。 | `version_num=0022_scope_taxonomy_aliases` |

## 账户、收藏与作品记录

| 表 | 数据与用途 | 示例 |
| --- | --- | --- |
| `user` | 登录账户、密码哈希、验证状态和权限标志。 | `email=reader@example.test, password=<hash>, is_active=true` |
| `user_profile` | 昵称、头像、简介和界面语言等偏好。 | `user_id=示例用户, nickname=Reader, language=ja-JP` |
| `social_identity` | 登录账户与外部身份提供商的关联。 | `user_id=示例用户, provider=github, subject=example-id` |
| `email_verification` | 邮箱验证码或重置验证、用途、过期、使用状态和尝试次数。 | `email=reader@example.test, code=<redacted>, is_used=false` |
| `refresh_token` | 会话刷新令牌记录、所属用户和有效期。 | `user_id=示例用户, token=<redacted>, jti=示例会话 ID` |
| `refresh_token_revocation` | 标记一条刷新令牌已撤销。 | `token_id=示例令牌记录, revoked_at=2026-11-24T04:00:00Z` |
| `user_library_entry` | 用户对作品的观看或游玩状态、自身评分、短评和可见性。 | `user_id=示例用户, entity_id=芙莉莲第二季, status=finished, rating=9` |
| `user_episode_progress` | 一条用户作品记录下，每集的完成状态。 | `user_subject_id=示例收藏记录, episode_entity_id=第一集, is_finished=true` |
| `user_release` | 某个用户具体体验的发行版本、平台、语言和完成日期。 | `library_entry_id=示例收藏记录, release_id=PC 版, language=ja, platform=Windows` |
| `user_subject_rating_detail` | 用户自己的分项评分，以键和值保存。 | `user_subject_id=示例收藏记录, key=story, value=9` |
| `user_tag` | 用户为整理自己资料库而创建的标签。 | `user_id=示例用户, name=待重看` |
| `user_library_entry_tag` | 用户标签和用户作品记录的多对多关系。 | `user_subject_id=示例收藏记录, tag_id=待重看` |
| `user_collection` | 用户创建的片单或作品清单、说明和公开设置。 | `user_id=示例用户, name=冬季动画, is_public=true` |
| `user_collection_item` | 清单中的用户作品记录和顺序。 | `collection_id=冬季动画清单, user_subject_id=示例收藏记录, order=1` |
| `user_review` | 用户的长篇作品评论、公开设置和剧透标记。 | `user_subject_id=示例收藏记录, title=旅途与时间, is_spoiler=false` |

## 社区

| 表 | 数据与用途 | 示例 |
| --- | --- | --- |
| `community_post` | 帖子内容、作者、关联作品、可见性和互动计数。 | `author_id=示例用户, entity_id=芙莉莲第二季, content=聊聊本季的配乐` |
| `community_comment` | 对帖子、动态、评论文章或清单的留言和楼中楼关系。 | `post_id=示例帖子, author_id=另一示例用户, content=很喜欢这段音乐` |
| `community_activity` | 可出现在动态流中的用户行为、实体引用、分组和去重。 | `activity_type=review_created, review_id=示例长评, user_id=示例用户` |
| `community_reaction` | 对社区对象的点赞等反应。 | `post_id=示例帖子, user_id=示例用户, reaction_type=like` |
| `community_bookmark` | 用户收藏的帖子、长评或清单。 | `post_id=示例帖子, user_id=示例用户` |
| `community_notification` | 发送给用户的社区通知、来源对象和已读时间。 | `recipient_id=示例用户, comment_id=示例留言, read_at=NULL` |
| `community_report` | 对内容或用户的举报、原因、处理状态和处理人。 | `reporter_id=示例用户, post_id=示例帖子, status=pending` |
| `community_moderation_action` | 社区管理操作、理由、执行人和目标。 | `moderator_id=示例管理员, post_id=示例帖子, action_type=hide` |
| `community_user_follow` | 用户之间的关注关系。 | `follower_id=读者 A, following_id=作者 B` |
| `community_user_block` | 用户之间的拉黑关系和理由。 | `user_id=示例用户 A, blocked_user_id=示例用户 B` |
| `community_user_mute` | 用户对另一账号的静音关系。 | `user_id=示例用户 A, muted_user_id=示例用户 B` |

## 生产 `0009` 的旧对象

下表补充 `0009_retire_schema_aliases` 中存在、在新版迁移中替换或退役的对象。PostgreSQL 的 `pg_stat_statements` 与 `pg_stat_statements_info` 是扩展视图。

| 对象 | 数据、用途和去向 | 示例 |
| --- | --- | --- |
| `entity_redirect` | 旧版归并方向和有效状态，迁移为 `entity_identity_membership`。 | `source_entity_id=来源作品 UUID, target_entity_id=规范作品 UUID, is_active=true` |
| `index_term_alias` | 旧版术语异写表，保留限定范围的映射并更名为 `taxonomy_alias`。 | `source_text=SF, normalized_key=sf, term_id=科幻` |
| `entity_display_profile` | 旧版标题、简介及审核记录，迁入版本化发布结构。 | `entity_id=示例作品, language=en, state=approved, title_text=Example Work` |
| `galgame_profile` | 旧版视觉小说开发状态及来源汇总游玩时长。开发状态已映射为事实，迁移验证来源可恢复性后退役该表。 | `work_id=示例视觉小说, development_status=finished, playtime_minutes=1800` |
| `metric_snapshot` | 旧版外站统计时间序列，迁至 `ranking.provider_metric`。 | `metric=votes, value=2000, provider_record_id=来源条目 UUID` |
| `metric_current` | 旧版来源统计的当前值缓存。 | `metric=score, value=8.2, provider_record_id=来源条目 UUID` |
| `metric_daily` | 旧版来源统计的每日汇总。 | 一条来源作品的某日评分记录，例如 `metric=score, value=8.2` |
| `entity_metric_current` | 旧版当前指标查询视图。 | 从来源当前指标得到某个作品的评分。 |

[目录数据模型](data-model.md) · [目录处理流程](catalogue-pipeline.md)
