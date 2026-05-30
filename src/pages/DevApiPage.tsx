import { useState } from 'react';
import { useAuth } from '@/features/auth/use-auth';
import { ApiError } from '@/lib/api/client';
import { authApi, profileApi } from '@/features/auth/api';
import {
  collectionsApi,
  progressApi,
  ratingDetailsApi,
  reviewsApi,
  tagsApi,
  userSubjectsApi,
} from '@/features/library/api';
import { activitiesApi, followsApi, publicUsersApi } from '@/features/social/api';
import { indexApi } from '@/features/subjects/api';
import { syncApi } from '@/features/sync/api';
import type { ActivityType, RatingDetail, UserSubjectStatus } from '@/lib/api/types';
import { Page } from '@/shared/ui/Page';

type DevResult = {
  action: string;
  ok: boolean;
  data: unknown;
};

function toDisplayError(error: unknown) {
  if (error instanceof ApiError) {
    return {
      name: error.name,
      message: error.message,
      status: error.status,
      code: error.code,
      data: error.data,
      url: error.url,
    };
  }

  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
    };
  }

  return error;
}

export function DevApiPage() {
  const auth = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [nickname, setNickname] = useState('');
  const [keyword, setKeyword] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [userSubjectId, setUserSubjectId] = useState('');
  const [userSubjectStatus, setUserSubjectStatus] = useState<UserSubjectStatus>('doing');
  const [simpleRating, setSimpleRating] = useState('4');
  const [rating, setRating] = useState('8.5');
  const [comment, setComment] = useState('');
  const [episodeId, setEpisodeId] = useState('');
  const [finishedEpisodeIds, setFinishedEpisodeIds] = useState('');
  const [tagNames, setTagNames] = useState('favorite,rewatch');
  const [ratingDetails, setRatingDetails] = useState('[{"key":"story","value":"8.5"}]');
  const [reviewId, setReviewId] = useState('');
  const [reviewTitle, setReviewTitle] = useState('My review title');
  const [reviewContent, setReviewContent] = useState('My review content.');
  const [collectionId, setCollectionId] = useState('');
  const [collectionItemId, setCollectionItemId] = useState('');
  const [collectionName, setCollectionName] = useState('Favorites');
  const [collectionNote, setCollectionNote] = useState('');
  const [collectionRelation, setCollectionRelation] = useState('main');
  const [collectionOrder, setCollectionOrder] = useState('1');
  const [targetUserId, setTargetUserId] = useState('');
  const [activityType, setActivityType] = useState<ActivityType | ''>('');
  const [syncTaskName, setSyncTaskName] = useState('');
  const [syncBatchSize, setSyncBatchSize] = useState('10');
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [result, setResult] = useState<DevResult | null>(null);

  async function run(action: string, task: () => Promise<unknown>) {
    setPendingAction(action);
    try {
      setResult({
        action,
        ok: true,
        data: await task(),
      });
    } catch (error) {
      setResult({
        action,
        ok: false,
        data: toDisplayError(error),
      });
    } finally {
      setPendingAction(null);
    }
  }

  function parsePositiveInteger(value: string) {
    const number = Number(value.trim());

    if (!Number.isInteger(number) || number < 1) {
      throw new Error('请输入大于等于 1 的整数 ID。');
    }

    return number;
  }

  function parsePositiveIntegerList(value: string) {
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
      .map(parsePositiveInteger);
  }

  function parseOptionalPositiveInteger(value: string) {
    return value.trim() ? parsePositiveInteger(value) : undefined;
  }

  function parseStringList(value: string) {
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function parseRatingDetails() {
    return JSON.parse(ratingDetails) as RatingDetail[];
  }

  function parseOptionalNumber(value: string) {
    return value.trim() ? Number(value) : undefined;
  }

  function parseOptionalActivityType(value: ActivityType | '') {
    return value || undefined;
  }

  return (
    <Page title="API 调试">
      <div className="dev-grid">
        <section className="dev-panel">
          <h2>认证</h2>
          <label className="field">
            <span>Email</span>
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          <label className="field">
            <span>Code</span>
            <input value={code} onChange={(event) => setCode(event.target.value)} />
          </label>
          <label className="field">
            <span>Nickname</span>
            <input value={nickname} onChange={(event) => setNickname(event.target.value)} />
          </label>
          <div className="button-row">
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('send register code', () => authApi.sendCode({ email, purpose: 'register' }))}
            >
              Send register code
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('send login code', () => authApi.sendCode({ email, purpose: 'login' }))}
            >
              Send login code
            </button>
            <button
              className="button button-primary"
              type="button"
              onClick={() => run('password login', () => auth.loginWithPassword({ email, password }))}
            >
              登录
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('code login', () => auth.loginWithCode({ email, code }))}
            >
              Code login
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('register', () => auth.register({ email, password, nickname, code }))}
            >
              Register
            </button>
            <button className="button button-secondary" type="button" onClick={() => run('refresh session', auth.refreshSession)}>
              Refresh
            </button>
            <button className="button button-secondary" type="button" onClick={() => run('logout', auth.logout)}>
              Logout
            </button>
          </div>
          <pre className="state-box">
            {JSON.stringify(
              {
                status: auth.status,
                role: auth.role,
                isAuthenticated: auth.isAuthenticated,
                profile: auth.profile,
              },
              null,
              2,
            )}
          </pre>
        </section>

        <section className="dev-panel">
          <h2>用户作品</h2>
          <label className="field">
            <span>Status</span>
            <select
              className="select-control"
              value={userSubjectStatus}
              onChange={(event) => setUserSubjectStatus(event.target.value as UserSubjectStatus)}
            >
              <option value="wish">wish</option>
              <option value="doing">doing</option>
              <option value="done">done</option>
              <option value="on_hold">on_hold</option>
              <option value="drop">drop</option>
            </select>
          </label>
          <label className="field">
            <span>Simple rating</span>
            <input value={simpleRating} onChange={(event) => setSimpleRating(event.target.value)} />
          </label>
          <label className="field">
            <span>Rating</span>
            <input value={rating} onChange={(event) => setRating(event.target.value)} />
          </label>
          <label className="field">
            <span>Comment</span>
            <input value={comment} onChange={(event) => setComment(event.target.value)} />
          </label>
          <div className="button-row">
            <button className="button button-secondary" type="button" onClick={() => run('my subjects', () => userSubjectsApi.listMine())}>
              My subjects
            </button>
            <button
              className="button button-primary"
              type="button"
              onClick={() =>
                run('mark subject', () =>
                  userSubjectsApi.createMine({
                    subject_id: subjectId,
                    status: userSubjectStatus,
                    simple_rating: parseOptionalNumber(simpleRating),
                    rating: rating.trim() || undefined,
                    comment,
                    is_public: true,
                  }),
                )
              }
            >
              Mark subject
            </button>
          </div>
        </section>

        <section className="dev-panel">
          <h2>接口</h2>
          <label className="field">
            <span>Keyword</span>
            <input value={keyword} onChange={(event) => setKeyword(event.target.value)} />
          </label>
          <label className="field">
            <span>Subject ID</span>
            <input value={subjectId} onChange={(event) => setSubjectId(event.target.value)} />
          </label>
          <label className="field">
            <span>UserSubject ID</span>
            <input value={userSubjectId} onChange={(event) => setUserSubjectId(event.target.value)} />
          </label>
          <div className="button-row">
            <button className="button button-secondary" type="button" onClick={() => run('me profile', profileApi.getMe)}>
              Profile
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('subjects search', () => indexApi.listSubjects({ keyword, page: 1, page_size: 16 }))}
            >
              Subjects
            </button>
            <button className="button button-secondary" type="button" onClick={() => run('calendar', () => indexApi.getCalendar())}>
              Calendar
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('subject detail', () => indexApi.getSubject(subjectId))}
            >
              Subject detail
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('subject episodes', () => indexApi.listSubjectEpisodes(subjectId))}
            >
              Episodes
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('subject staff', () => indexApi.listSubjectStaff(subjectId))}
            >
              Staff
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('subject characters', () => indexApi.listSubjectCharacters(subjectId))}
            >
              Characters
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('subject relations', () => indexApi.listSubjectRelations(subjectId))}
            >
              Relations
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('my subject context', () => userSubjectsApi.getContext(subjectId))}
            >
              My context
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('get my subject', () => userSubjectsApi.getMine(parsePositiveInteger(userSubjectId)))}
            >
              Get my subject
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('delete my subject', () => userSubjectsApi.deleteMine(parsePositiveInteger(userSubjectId)))}
            >
              Delete mark
            </button>
          </div>
        </section>

        <section className="dev-panel">
          <h2>进度 / 标签 / 评分 / 评论</h2>
          <label className="field">
            <span>Episode ID</span>
            <input value={episodeId} onChange={(event) => setEpisodeId(event.target.value)} />
          </label>
          <label className="field">
            <span>Finished episode IDs</span>
            <input value={finishedEpisodeIds} onChange={(event) => setFinishedEpisodeIds(event.target.value)} />
          </label>
          <label className="field">
            <span>Tag names</span>
            <input value={tagNames} onChange={(event) => setTagNames(event.target.value)} />
          </label>
          <label className="field">
            <span>Rating details JSON</span>
            <input value={ratingDetails} onChange={(event) => setRatingDetails(event.target.value)} />
          </label>
          <label className="field">
            <span>Review ID</span>
            <input value={reviewId} onChange={(event) => setReviewId(event.target.value)} />
          </label>
          <label className="field">
            <span>Review title</span>
            <input value={reviewTitle} onChange={(event) => setReviewTitle(event.target.value)} />
          </label>
          <label className="field">
            <span>Review content</span>
            <input value={reviewContent} onChange={(event) => setReviewContent(event.target.value)} />
          </label>
          <div className="button-row">
            <button className="button button-secondary" type="button" onClick={() => run('progress', () => progressApi.get(subjectId))}>
              Progress
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() =>
                run('replace progress', () => progressApi.replaceFinishedEpisodes(subjectId, parsePositiveIntegerList(finishedEpisodeIds)))
              }
            >
              Replace progress
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('episode finished', () => progressApi.setEpisodeFinished(subjectId, parsePositiveInteger(episodeId), true))}
            >
              Episode done
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('episode unfinished', () => progressApi.setEpisodeFinished(subjectId, parsePositiveInteger(episodeId), false))}
            >
              Episode undone
            </button>
            <button className="button button-secondary" type="button" onClick={() => run('subject tags', () => tagsApi.getForSubject(subjectId))}>
              Tags
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('replace tags', () => tagsApi.replaceForSubject(subjectId, { tag_names: parseStringList(tagNames) }))}
            >
              Replace tags
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('rating details', () => ratingDetailsApi.getForSubject(subjectId))}
            >
              Rating details
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('replace rating details', () => ratingDetailsApi.replaceForSubject(subjectId, parseRatingDetails()))}
            >
              Replace ratings
            </button>
            <button className="button button-secondary" type="button" onClick={() => run('my reviews', () => reviewsApi.listMine())}>
              My reviews
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('subject reviews', () => reviewsApi.listForSubject(subjectId))}
            >
              Subject reviews
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() =>
                run('create review', () =>
                  reviewsApi.createForSubject(subjectId, {
                    title: reviewTitle,
                    content: reviewContent,
                    is_public: true,
                    is_spoiler: false,
                  }),
                )
              }
            >
              Create review
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('review detail', () => reviewsApi.getMine(parsePositiveInteger(reviewId)))}
            >
              Review detail
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() =>
                run('update review', () =>
                  reviewsApi.updateMine(parsePositiveInteger(reviewId), {
                    title: reviewTitle,
                    content: reviewContent,
                  }),
                )
              }
            >
              Update review
            </button>
            <button className="button button-secondary" type="button" onClick={() => run('delete review', () => reviewsApi.deleteMine(parsePositiveInteger(reviewId)))}>
              Delete review
            </button>
          </div>
        </section>

        <section className="dev-panel">
          <h2>集合</h2>
          <label className="field">
            <span>Collection ID</span>
            <input value={collectionId} onChange={(event) => setCollectionId(event.target.value)} />
          </label>
          <label className="field">
            <span>Collection item ID</span>
            <input value={collectionItemId} onChange={(event) => setCollectionItemId(event.target.value)} />
          </label>
          <label className="field">
            <span>Collection name</span>
            <input value={collectionName} onChange={(event) => setCollectionName(event.target.value)} />
          </label>
          <label className="field">
            <span>Collection note</span>
            <input value={collectionNote} onChange={(event) => setCollectionNote(event.target.value)} />
          </label>
          <label className="field">
            <span>Relation</span>
            <input value={collectionRelation} onChange={(event) => setCollectionRelation(event.target.value)} />
          </label>
          <label className="field">
            <span>Order</span>
            <input value={collectionOrder} onChange={(event) => setCollectionOrder(event.target.value)} />
          </label>
          <div className="button-row">
            <button className="button button-secondary" type="button" onClick={() => run('my collections', () => collectionsApi.listMine())}>
              Collections
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() =>
                run('create collection', () =>
                  collectionsApi.createMine({
                    name: collectionName,
                    simple_rating: parseOptionalNumber(simpleRating),
                    note: collectionNote,
                    is_public: true,
                  }),
                )
              }
            >
              Create collection
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('collection detail', () => collectionsApi.getMine(parsePositiveInteger(collectionId)))}
            >
              Collection detail
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() =>
                run('update collection', () =>
                  collectionsApi.updateMine(parsePositiveInteger(collectionId), {
                    name: collectionName,
                    simple_rating: parseOptionalNumber(simpleRating),
                    note: collectionNote,
                  }),
                )
              }
            >
              Update collection
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('collection items', () => collectionsApi.listItems(parsePositiveInteger(collectionId)))}
            >
              Collection items
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() =>
                run('add collection item', () =>
                  collectionsApi.addItem(parsePositiveInteger(collectionId), {
                    subject_id: subjectId,
                    order: parseOptionalPositiveInteger(collectionOrder),
                    relation: collectionRelation,
                  }),
                )
              }
            >
              Add item
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() =>
                run('replace collection items', () =>
                  collectionsApi.replaceItems(parsePositiveInteger(collectionId), subjectId ? [{ subject_id: subjectId }] : []),
                )
              }
            >
              Replace items
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() =>
                run('delete collection item', () =>
                  collectionsApi.deleteItem(parsePositiveInteger(collectionId), parsePositiveInteger(collectionItemId)),
                )
              }
            >
              Delete item
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('delete collection', () => collectionsApi.deleteMine(parsePositiveInteger(collectionId)))}
            >
              Delete collection
            </button>
          </div>
        </section>

        <section className="dev-panel">
          <h2>公开用户 / 关注 / 动态</h2>
          <label className="field">
            <span>Target user ID</span>
            <input value={targetUserId} onChange={(event) => setTargetUserId(event.target.value)} />
          </label>
          <label className="field">
            <span>Activity type</span>
            <select
              className="select-control"
              value={activityType}
              onChange={(event) => setActivityType(event.target.value as ActivityType | '')}
            >
              <option value="">all</option>
              <option value="user_subject_created">user_subject_created</option>
              <option value="user_subject_updated">user_subject_updated</option>
              <option value="review_created">review_created</option>
              <option value="collection_created">collection_created</option>
              <option value="collection_item_added">collection_item_added</option>
              <option value="user_followed">user_followed</option>
            </select>
          </label>
          <div className="button-row">
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('public profile', () => publicUsersApi.getProfile(parsePositiveInteger(targetUserId)))}
            >
              Public profile
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('public subjects', () => publicUsersApi.listSubjects(parsePositiveInteger(targetUserId)))}
            >
              Public subjects
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('public reviews', () => publicUsersApi.listReviews(parsePositiveInteger(targetUserId)))}
            >
              Public reviews
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('public collections', () => publicUsersApi.listCollections(parsePositiveInteger(targetUserId)))}
            >
              Public collections
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('follow user', () => followsApi.follow(parsePositiveInteger(targetUserId)))}
            >
              Follow
            </button>
            <button className="button button-secondary" type="button" onClick={() => run('my following', () => followsApi.listMyFollowing())}>
              My following
            </button>
            <button className="button button-secondary" type="button" onClick={() => run('my followers', () => followsApi.listMyFollowers())}>
              My followers
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('public following', () => followsApi.listPublicFollowing(parsePositiveInteger(targetUserId)))}
            >
              Public following
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('public followers', () => followsApi.listPublicFollowers(parsePositiveInteger(targetUserId)))}
            >
              Public followers
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('unfollow user', () => followsApi.unfollow(parsePositiveInteger(targetUserId)))}
            >
              Unfollow
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('my activities', () => activitiesApi.listMine({ activity_type: parseOptionalActivityType(activityType) }))}
            >
              My activities
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() =>
                run('public activities', () =>
                  activitiesApi.listPublic(parsePositiveInteger(targetUserId), { activity_type: parseOptionalActivityType(activityType) }),
                )
              }
            >
              Public activities
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('feed', () => activitiesApi.listFeed({ activity_type: parseOptionalActivityType(activityType), include_self: true }))}
            >
              Feed
            </button>
          </div>
        </section>

        <section className="dev-panel">
          <h2>同步</h2>
          <label className="field">
            <span>Sync task name</span>
            <input value={syncTaskName} onChange={(event) => setSyncTaskName(event.target.value)} />
          </label>
          <label className="field">
            <span>Batch size</span>
            <input value={syncBatchSize} onChange={(event) => setSyncBatchSize(event.target.value)} />
          </label>
          <div className="button-row">
            <button className="button button-secondary" type="button" onClick={() => run('sync status', () => syncApi.getIncrementalStatus())}>
              Sync status
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() =>
                run('run incremental sync', () =>
                  syncApi.runIncremental({
                    run_async: false,
                    batch_size: parseOptionalPositiveInteger(syncBatchSize),
                    task_name: syncTaskName.trim() || undefined,
                  }),
                )
              }
            >
              Run incremental
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('run calendar sync', () => syncApi.runCalendar({ run_async: false, sync_subject_details: false }))}
            >
              Run calendar
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => run('resync subject', () => syncApi.resyncSubject(subjectId, { run_async: false }))}
            >
              Resync subject
            </button>
          </div>
        </section>
      </div>

      <section className="dev-result">
        <div className="dev-result-header">
          <h2>结果</h2>
          {pendingAction ? <span>{pendingAction}</span> : null}
        </div>
        <pre className={result?.ok ? 'state-box is-success' : 'state-box is-error'}>
          {result ? JSON.stringify(result, null, 2) : 'No result'}
        </pre>
      </section>
    </Page>
  );
}
