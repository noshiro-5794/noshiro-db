# Public User Profiles API

Run the common setup in [README](./README.md). Login with [Auth](./users-auth.md) only when testing `is_following`.

## Setup

Use an existing public user.

```bash
PUBLIC_USER_ID=2
```

If you are logged in, you can also get your own user ID:

```bash
MY_USER_ID=$(
  curl -s -X GET "$BASE_URL/api/users/me/profile/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    | tee /tmp/noshiro_my_profile.json | jq -r ".data.user_id // empty"
)

cat /tmp/noshiro_my_profile.json | jq
echo "$MY_USER_ID"
```

## Get Public Profile

Unauthenticated request:

```bash
curl -s -X GET "$BASE_URL/api/users/$PUBLIC_USER_ID/profile/" | jq
```

Authenticated request, useful for checking `is_following`:

```bash
curl -s -X GET "$BASE_URL/api/users/$PUBLIC_USER_ID/profile/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected success response shape:

```json
{
  "code": 0,
  "message": "",
  "data": {
    "id": 2,
    "nickname": "target nickname",
    "avatar": "",
    "bio": "",
    "stats": {
      "subject_count": 0,
      "review_count": 0,
      "collection_count": 0,
      "following_count": 0,
      "follower_count": 0
    },
    "is_following": false
  }
}
```

Missing user, expected to fail:

```bash
curl -s -X GET "$BASE_URL/api/users/999999/profile/" | jq
```

Expected business error:

```json
{
  "code": 11201,
  "message": "user not found",
  "data": null
}
```

## List Public Subjects

This endpoint is paginated and returns only `is_public=true` user subject records.

```bash
curl -s -X GET "$BASE_URL/api/users/$PUBLIC_USER_ID/subjects/?page=1&page_size=16" | jq
```

Filter by status:

```bash
curl -s -X GET "$BASE_URL/api/users/$PUBLIC_USER_ID/subjects/?status=done&page=1&page_size=16" | jq
```

Filter by subject type:

```bash
curl -s -X GET "$BASE_URL/api/users/$PUBLIC_USER_ID/subjects/?subject_type=anime&page=1&page_size=16" | jq
```

Search:

```bash
curl -s -X GET "$BASE_URL/api/users/$PUBLIC_USER_ID/subjects/?keyword=test&page=1&page_size=16" | jq
```

Ordering:

```bash
curl -s -X GET "$BASE_URL/api/users/$PUBLIC_USER_ID/subjects/?ordering=-rating&page=1&page_size=16" | jq
```

Supported ordering values:

```text
id
-id
simple_rating
-simple_rating
rating
-rating
watch_start_date
-watch_start_date
watch_end_date
-watch_end_date
```

## List Public Reviews

This endpoint is paginated and returns only reviews whose user subject is public and whose review is public.

```bash
curl -s -X GET "$BASE_URL/api/users/$PUBLIC_USER_ID/reviews/?page=1&page_size=16" | jq
```

Search:

```bash
curl -s -X GET "$BASE_URL/api/users/$PUBLIC_USER_ID/reviews/?keyword=test&page=1&page_size=16" | jq
```

Ordering:

```bash
curl -s -X GET "$BASE_URL/api/users/$PUBLIC_USER_ID/reviews/?ordering=-created_at&page=1&page_size=16" | jq
```

Supported ordering values:

```text
id
-id
created_at
-created_at
```

## List Public Collections

This endpoint is paginated and returns only `is_public=true` collections.

```bash
curl -s -X GET "$BASE_URL/api/users/$PUBLIC_USER_ID/collections/?page=1&page_size=16" | jq
```

Search:

```bash
curl -s -X GET "$BASE_URL/api/users/$PUBLIC_USER_ID/collections/?keyword=favorites&page=1&page_size=16" | jq
```

Ordering:

```bash
curl -s -X GET "$BASE_URL/api/users/$PUBLIC_USER_ID/collections/?ordering=-item_count&page=1&page_size=16" | jq
```

Supported ordering values:

```text
id
-id
name
-name
simple_rating
-simple_rating
item_count
-item_count
```

## Privacy Checks

Create or update a private collection:

```bash
PRIVATE_COLLECTION_ID=$(
  curl -s -X POST "$BASE_URL/api/users/me/collections/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "Private collection",
      "is_public": false
    }' | tee /tmp/noshiro_private_collection.json | jq -r ".data.id // empty"
)

cat /tmp/noshiro_private_collection.json | jq
echo "$PRIVATE_COLLECTION_ID"
```

Then verify it does not appear in the public collection list:

```bash
curl -s -X GET "$BASE_URL/api/users/$MY_USER_ID/collections/?keyword=Private%20collection" | jq
```

Expected result: `data.results` is empty.

## Frontend Flow

On a public user page:

1. Load profile summary from `GET /api/users/{user_id}/profile/`.
2. Load tab content from `subjects`, `reviews`, `collections`, `following`, or `followers` endpoints only when that tab is opened.
3. If the viewer is logged in, call the profile endpoint with `Authorization` so `is_following` reflects the current user.
4. Use the follow APIs from [Follows](./users-follows.md) to toggle follow state.
