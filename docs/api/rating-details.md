# Rating Details API

Run the common setup in [README](./README.md), then login with [Auth](./auth.md) to set `ACCESS_TOKEN`.

## Setup

Use a subject that has already been marked by the current user.

```bash
SUBJECT_ID="000212ed-b7b4-45c1-8d0d-7cd72906baa4"
```

Important ID distinction:

- `subject_id` is the global subject UUID.
- New subject detail pages should use `subject_id` routes.
- `user_subject_id` rating detail routes are kept for compatibility with older screens.

## Get Rating Details

Recommended subject-scoped endpoint:

```bash
curl -s -X GET "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/rating-details/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Unmarked subject, expected to fail:

```bash
UNMARKED_SUBJECT_ID="00000000-0000-0000-0000-000000000000"

curl -s -X GET "$BASE_URL/api/users/me/subjects/$UNMARKED_SUBJECT_ID/rating-details/" \
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

## Replace Rating Details

This replaces the full rating detail set for the marked subject.

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/rating-details/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "details": [
      {
        "key": "story",
        "value": "8.5"
      },
      {
        "key": "music",
        "value": "9.0"
      },
      {
        "key": "visual",
        "value": "7.5"
      }
    ]
  }' | jq
```

Clear all rating details:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/rating-details/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "details": []
  }' | jq
```

Duplicate keys, expected to fail validation:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/rating-details/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "details": [
      {
        "key": "story",
        "value": "8.5"
      },
      {
        "key": "story",
        "value": "9.0"
      }
    ]
  }' | jq
```

Invalid value, expected to fail validation:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/rating-details/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "details": [
      {
        "key": "story",
        "value": "11.0"
      }
    ]
  }' | jq
```

Blank key, expected to fail validation:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$SUBJECT_ID/rating-details/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "details": [
      {
        "key": " ",
        "value": "8.0"
      }
    ]
  }' | jq
```

## Compatibility Endpoint

Older screens can still use `user_subject_id`:

```bash
USER_SUBJECT_ID=1

curl -s -X GET "$BASE_URL/api/users/me/subjects/$USER_SUBJECT_ID/rating-details/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

```bash
curl -s -X PUT "$BASE_URL/api/users/me/subjects/$USER_SUBJECT_ID/rating-details/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "details": [
      {
        "key": "story",
        "value": "8.5"
      }
    ]
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
3. Show `context.data.rating_details` as the initial value.
4. Save edited dimensions with `PUT /api/users/me/subjects/${subjectId}/rating-details/`.

Recommended request body:

```js
{
  details: [
    { key: "story", value: "8.5" },
    { key: "music", value: "9.0" },
  ],
}
```
