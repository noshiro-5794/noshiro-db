# Tags API

Run the common setup in [README](./README.md), then login with [Auth](./auth.md) to set `ACCESS_TOKEN`.

## Setup

Use a subject that has already been marked by the current user.

```bash
TAG_NAME_1="favorite"
TAG_NAME_2="rewatch"
SUBJECT_ID="000212ed-b7b4-45c1-8d0d-7cd72906baa4"
```

Important ID distinction:

- `tag_id` is the current user's tag resource ID.
- `subject_id` is the global subject UUID.
- New subject detail pages should use `subject_id` routes.
- `user_subject_id` tag routes are kept for compatibility with older screens.

## List My Tags

This endpoint is paginated.

```bash
curl -s -X GET "$BASE_URL/api/users/me/tags/?page=1&page_size=16" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

## Create Or Reuse Tag

This endpoint creates a tag if the name does not exist. If the current user already has a tag with the same name, the existing tag is returned.

```bash
TAG_ID_1=$(
  curl -s -X POST "$BASE_URL/api/users/me/tags/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"$TAG_NAME_1\"
    }" | tee /tmp/noshiro_create_tag_1.json | jq -r ".data.id // empty"
)

cat /tmp/noshiro_create_tag_1.json | jq
echo "$TAG_ID_1"
```

Create a second tag:

```bash
TAG_ID_2=$(
  curl -s -X POST "$BASE_URL/api/users/me/tags/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"$TAG_NAME_2\"
    }" | tee /tmp/noshiro_create_tag_2.json | jq -r ".data.id // empty"
)

cat /tmp/noshiro_create_tag_2.json | jq
echo "$TAG_ID_2"
```

Same tag name, expected to reuse the existing tag:

```bash
curl -s -X POST "$BASE_URL/api/users/me/tags/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$TAG_NAME_1\"
  }" | jq
```

Expected success response:

```json
{
  "code": 0,
  "message": "",
  "data": {
    "id": 1,
    "name": "favorite"
  }
}
```

## Update Tag

```bash
curl -s -X PATCH "$BASE_URL/api/users/me/tags/$TAG_ID_1/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "favorite-updated"
  }' | jq
```

Update missing tag, expected to fail:

```bash
curl -s -X PATCH "$BASE_URL/api/users/me/tags/999999/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "missing"
  }' | jq
```

## Bind Tags To Subject

Recommended subject-scoped endpoint:

The most ergonomic frontend flow is to send tag names. Missing tags are created automatically, and existing same-name tags are reused.

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/tags/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tag_names\": [\"$TAG_NAME_1\", \"$TAG_NAME_2\"]
  }" | jq
```

This replaces the full tag set for the marked subject.

Duplicate tag names are accepted and deduplicated:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/tags/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tag_names\": [\"$TAG_NAME_1\", \"$TAG_NAME_1\", \"$TAG_NAME_2\"]
  }" | jq
```

The ID-based format is still supported:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/tags/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tag_ids\": [$TAG_ID_1, $TAG_ID_2]
  }" | jq
```

Duplicate tag IDs are accepted and deduplicated:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/tags/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tag_ids\": [$TAG_ID_1, $TAG_ID_1, $TAG_ID_2]
  }" | jq
```

Clear subject tags:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/tags/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tag_ids": []
  }' | jq
```

Invalid tag ID, expected to fail:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/tags/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tag_ids": [999999]
  }' | jq
```

Unmarked subject, expected to fail:

```bash
UNMARKED_SUBJECT_ID="00000000-0000-0000-0000-000000000000"

curl -s -X PUT "$BASE_URL/api/users/me/subjects/$UNMARKED_SUBJECT_ID/tags/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tag_names\": [\"$TAG_NAME_1\"]
  }" | jq
```

Expected business error:

```json
{
  "code": 12100,
  "message": "user subject not found",
  "data": null
}
```

## Get Subject Tags

Recommended subject-scoped endpoint:

```bash
curl -s -X GET "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/tags/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

## Compatibility Endpoint

Older screens can still use `user_subject_id`:

```bash
USER_SUBJECT_ID=1

curl -s -X GET "$BASE_URL/api/users/me/subjects/$USER_SUBJECT_ID/tags/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$USER_SUBJECT_ID/tags/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tag_ids\": [$TAG_ID_1, $TAG_ID_2]
  }" | jq
```

## Delete Tag

Deleting a tag also removes its subject bindings.

```bash
curl -s -X DELETE "$BASE_URL/api/users/me/tags/$TAG_ID_1/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Delete missing tag, expected to fail:

```bash
curl -s -X DELETE "$BASE_URL/api/users/me/tags/999999/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
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
3. Let the user type tag names or pick existing tags.
4. Bind selected tags with `PUT /api/users/me/subjects/${subjectId}/tags/`.

Recommended request body:

```js
{
  tag_names: ["favorite", "rewatch"]
}
```
