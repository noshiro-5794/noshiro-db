# User Subjects API

Run the common setup in [README](./README.md), then login with [Auth](./auth.md) to set `ACCESS_TOKEN`.

## List My Subjects

Unauthenticated request, expected to fail:

```bash
curl -s -X GET "$BASE_URL/api/users/me/subjects/" | jq
```

Authenticated request:

```bash
curl -s -X GET "$BASE_URL/api/users/me/subjects/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Filter by status:

```bash
curl -s -X GET "$BASE_URL/api/users/me/subjects/?status=done" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

## Create My Subject

```bash
curl -s -X POST "$BASE_URL/api/users/me/subjects/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject_id": "00001a56-b41f-4376-91db-1e10c65794bb",
    "status": "done",
    "simple_rating": 4,
    "rating": "8.5",
    "comment": "This is a comment.",
    "watch_start_date": "2024-01-01",
    "watch_end_date": "2024-01-10",
    "is_public": true
  }' | jq
```

## Get My Subject

```bash
curl -s -X GET "$BASE_URL/api/users/me/subjects/1/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

## Get My Context For A Subject

Use this endpoint on a subject detail page after login. It returns the current user's mark state, tags, rating details, reviews, and progress summary for a global `subject_id`.

```bash
SUBJECT_ID="000212ed-b7b4-45c1-8d0d-7cd72906baa4"

curl -s -X GET "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/context/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Unmarked response shape:

```json
{
  "code": 0,
  "message": "",
  "data": {
    "is_marked": false,
    "user_subject": null,
    "tags": [],
    "rating_details": [],
    "reviews": [],
    "progress": {
      "finished_count": 0,
      "finished_episode_ids": []
    }
  }
}
```

Marked response shape:

```json
{
  "code": 0,
  "message": "",
  "data": {
    "is_marked": true,
    "user_subject": {
      "id": 1,
      "status": "doing",
      "simple_rating": 4,
      "rating": "8.5",
      "comment": "",
      "watch_start_date": "",
      "watch_end_date": "",
      "is_public": true,
      "subject": {
        "id": "000212ed-b7b4-45c1-8d0d-7cd72906baa4",
        "title": "title"
      }
    },
    "tags": [],
    "rating_details": [],
    "reviews": [],
    "progress": {
      "finished_count": 0,
      "finished_episode_ids": []
    }
  }
}
```

Frontend detail-page flow:

```js
const context = await fetch(`${baseUrl}/api/users/me/subjects/${subjectId}/context/`, {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
}).then((response) => response.json());

if (!context.data.is_marked) {
  // Show "mark this subject" controls first.
} else {
  // Show my status, tags, rating details, reviews, and progress.
}
```

`user_subject.id` is still returned for backward compatibility with older nested APIs, but new subject detail pages should prefer subject-scoped APIs such as this context endpoint.

## Update My Subject

```bash
curl -s -X PATCH "$BASE_URL/api/users/me/subjects/1/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "simple_rating": 5,
    "rating": "9.0",
    "comment": "updated comment",
    "is_public": false
  }' | jq
```

Invalid rating example, expected to fail:

```bash
curl -s -X PATCH "$BASE_URL/api/users/me/subjects/1/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "simple_rating": 6
  }' | jq
```

## Delete My Subject

```bash
curl -s -X DELETE "$BASE_URL/api/users/me/subjects/1/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Get deleted subject, expected to fail:

```bash
curl -s -X GET "$BASE_URL/api/users/me/subjects/1/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```
