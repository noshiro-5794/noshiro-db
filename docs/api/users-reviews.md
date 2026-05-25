# Reviews API

Run the common setup in [README](./README.md), then login with [Auth](./users-auth.md) to set `ACCESS_TOKEN`.

## Setup

Use a subject that has already been marked by the current user.

```bash
SUBJECT_ID="000212ed-b7b4-45c1-8d0d-7cd72906baa4"
```

Important ID distinction:

- `subject_id` is the global subject UUID.
- New subject detail pages should use `subject_id` routes.
- `user_subject_id` review creation route is kept for compatibility with older screens.

## List My Reviews

This endpoint is paginated.

```bash
curl -s -X GET "$BASE_URL/api/users/me/reviews/?page=1&page_size=16" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Search by title or content:

```bash
curl -s -X GET "$BASE_URL/api/users/me/reviews/?keyword=story&page=1&page_size=16" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Ordering:

```bash
curl -s -X GET "$BASE_URL/api/users/me/reviews/?ordering=-created_at" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Supported ordering values:

```text
created_at
-created_at
id
-id
```

## List My Reviews For Subject

Recommended subject-scoped endpoint:

```bash
curl -s -X GET "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/reviews/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Unmarked subject, expected to fail:

```bash
UNMARKED_SUBJECT_ID="00000000-0000-0000-0000-000000000000"

curl -s -X GET "$BASE_URL/api/users/me/subjects/$UNMARKED_SUBJECT_ID/reviews/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected business error:

```json
{
  "code": 12100,
  "message": "user subject not found",
  "data": null
}
```

## Create Review For Subject

Recommended subject-scoped endpoint:

```bash
REVIEW_ID=$(
  curl -s -X POST "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/reviews/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "title": "My review title",
      "content": "My review content.",
      "is_public": true,
      "is_spoiler": false
    }' | tee /tmp/noshiro_create_review.json | jq -r ".data.id // empty"
)

cat /tmp/noshiro_create_review.json | jq
echo "$REVIEW_ID"
```

Blank title, expected to fail validation:

```bash
curl -s -X POST "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/reviews/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": " ",
    "content": "My review content."
  }' | jq
```

Blank content, expected to fail validation:

```bash
curl -s -X POST "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/reviews/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My review title",
    "content": " "
  }' | jq
```

## Get Review Detail

```bash
curl -s -X GET "$BASE_URL/api/users/me/reviews/$REVIEW_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Missing review, expected to fail:

```bash
curl -s -X GET "$BASE_URL/api/users/me/reviews/999999/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected business error:

```json
{
  "code": 12300,
  "message": "review not found",
  "data": null
}
```

## Update Review

```bash
curl -s -X PATCH "$BASE_URL/api/users/me/reviews/$REVIEW_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated review title",
    "content": "Updated review content.",
    "is_public": false,
    "is_spoiler": true
  }' | jq
```

Partial update:

```bash
curl -s -X PATCH "$BASE_URL/api/users/me/reviews/$REVIEW_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_spoiler": false
  }' | jq
```

## Delete Review

```bash
curl -s -X DELETE "$BASE_URL/api/users/me/reviews/$REVIEW_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Get deleted review, expected to fail:

```bash
curl -s -X GET "$BASE_URL/api/users/me/reviews/$REVIEW_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

## Compatibility Endpoint

Older screens can still create by `user_subject_id`:

```bash
USER_SUBJECT_ID=1

curl -s -X POST "$BASE_URL/api/users/me/subjects/$USER_SUBJECT_ID/reviews/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My review title",
    "content": "My review content.",
    "is_public": true,
    "is_spoiler": false
  }' | jq
```

## Frontend Flow

On a subject detail page:

1. Load subject context:

```js
const context = await fetch(`${baseUrl}/api/users/me/subjects/${subjectId}/context/`, {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
}).then((response) => response.json());
```

2. If `context.data.is_marked` is false, ask the user to mark the subject first.
3. Show `context.data.reviews` as the initial value.
4. Create reviews with `POST /api/users/me/subjects/${subjectId}/reviews/`.
5. Update or delete reviews by `review_id`.

Recommended create body:

```js
{
  title: "My review title",
  content: "My review content.",
  is_public: true,
  is_spoiler: false,
}
```
