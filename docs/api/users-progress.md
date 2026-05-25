# Episode Progress API

Run the common setup in [README](./README.md), then login with [Auth](./users-auth.md) to set `ACCESS_TOKEN`.

## Setup

Use a subject that has episodes.

```bash
PROGRESS_SUBJECT_ID="000212ed-b7b4-45c1-8d0d-7cd72906baa4"
EPISODE_ID_1=722044
EPISODE_ID_2=722045
INVALID_EPISODE_ID=1
```

Important ID distinction:

- `user_subject_id` is the user's collection/mark record ID, for example `3`.
- `subject_id` is the global subject UUID, for example `000212ed-b7b4-45c1-8d0d-7cd72906baa4`.
- Progress APIs use `subject_id`, not `user_subject_id`.

If the frontend starts from `GET /api/users/me/subjects/`, use `item.subject.id` as `PROGRESS_SUBJECT_ID`, not `item.id`.

Wrong:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/3/episodes/progress/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"finished_episode_ids\": [$EPISODE_ID_1, $EPISODE_ID_2]
  }" | jq
```

Right:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$PROGRESS_SUBJECT_ID/episodes/progress/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"finished_episode_ids\": [$EPISODE_ID_1, $EPISODE_ID_2]
  }" | jq
```

## Get Progress Summary

```bash
curl -s -X GET "$BASE_URL/api/users/me/subjects/$PROGRESS_SUBJECT_ID/episodes/progress/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected shape:

```json
{
  "code": 0,
  "message": "",
  "data": {
    "subject_id": "000212ed-b7b4-45c1-8d0d-7cd72906baa4",
    "user_subject_id": null,
    "total_episodes": 24,
    "finished_count": 0,
    "finished_episode_ids": [],
    "episodes": [
      {
        "id": 722044,
        "title": "SWORD",
        "type": "0",
        "ep_num": 1,
        "sort": 1,
        "date": "2017-10-06",
        "is_finished": false
      }
    ]
  }
}
```

`user_subject_id` is `null` until the user has a `UserSubject` record for this subject.

## Replace Finished Episodes

This replaces the full finished episode set for this subject.

The subject must already be marked by the current user. Create a `UserSubject` first with `POST /api/users/me/subjects/` if needed.

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$PROGRESS_SUBJECT_ID/episodes/progress/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"finished_episode_ids\": [$EPISODE_ID_1, $EPISODE_ID_2]
  }" | jq
```

Empty list clears all finished progress:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$PROGRESS_SUBJECT_ID/episodes/progress/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "finished_episode_ids": []
  }' | jq
```

Duplicate episode IDs are accepted and deduplicated:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$PROGRESS_SUBJECT_ID/episodes/progress/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"finished_episode_ids\": [$EPISODE_ID_1, $EPISODE_ID_1, $EPISODE_ID_2]
  }" | jq
```

## Mark One Episode Finished

The subject must already be marked by the current user.

```bash
curl -s -X PATCH "$BASE_URL/api/users/me/subjects/$PROGRESS_SUBJECT_ID/episodes/$EPISODE_ID_1/progress/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_finished": true
  }' | jq
```

## Mark One Episode Unfinished

```bash
curl -s -X PATCH "$BASE_URL/api/users/me/subjects/$PROGRESS_SUBJECT_ID/episodes/$EPISODE_ID_1/progress/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_finished": false
  }' | jq
```

## Invalid Episode

Episode ID does not belong to the subject, expected to fail:

```bash
curl -s -X PATCH "$BASE_URL/api/users/me/subjects/$PROGRESS_SUBJECT_ID/episodes/$INVALID_EPISODE_ID/progress/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_finished": true
  }' | jq
```

## Invalid Subject

Nonexistent subject, expected to fail:

```bash
curl -s -X GET "$BASE_URL/api/users/me/subjects/00000000-0000-0000-0000-000000000000/episodes/progress/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

## Notes

- `GET` does not create a `UserSubject` record.
- `PUT` and `PATCH` require an existing `UserSubject` record.
- If the user has not marked the subject yet, `PUT` and `PATCH` return `user subject not found`.
- The response returns the complete episode list for one subject. It does not use pagination.

## Frontend Flow

When the user opens a marked subject from their own list:

1. Load my subjects:

```bash
curl -s -X GET "$BASE_URL/api/users/me/subjects/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

2. Pick the global subject UUID from the selected item:

```js
const userSubjectId = item.id;
const subjectId = item.subject.id;
```

3. Load episode progress:

```js
await fetch(`${baseUrl}/api/users/me/subjects/${subjectId}/episodes/progress/`, {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});
```

4. Mark one episode:

```js
await fetch(`${baseUrl}/api/users/me/subjects/${subjectId}/episodes/${episodeId}/progress/`, {
  method: "PATCH",
  headers: {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    is_finished: true,
  }),
});
```

The frontend can keep `userSubjectId` for APIs that operate on the user's mark record, such as tags, reviews, rating details, and collection item relations. Episode progress uses `subjectId`.

When the user opens an unmarked subject from a global subject page:

1. Allow read-only progress preview with `GET /episodes/progress/`.
2. Before enabling progress writes, ask the user to mark the subject first.
3. Create the mark with `POST /api/users/me/subjects/`.
4. Then call `PUT` or `PATCH` progress APIs with the global `subjectId`.
