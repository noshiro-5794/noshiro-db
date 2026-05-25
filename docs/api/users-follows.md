# Follows API

Run the common setup in [README](./README.md), then login with [Auth](./users-auth.md) to set `ACCESS_TOKEN`.

## Setup

Prepare another existing user as the follow target.

```bash
MY_USER_ID=$(
  curl -s -X GET "$BASE_URL/api/users/me/profile/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    | tee /tmp/noshiro_my_profile.json | jq -r ".data.user_id // empty"
)

cat /tmp/noshiro_my_profile.json | jq
echo "$MY_USER_ID"

TARGET_USER_ID=2
```

Important ID distinction:

- `MY_USER_ID` is the authenticated user.
- `TARGET_USER_ID` must be another user.
- Public following/follower list APIs do not require authentication.

## Follow User

```bash
curl -s -X POST "$BASE_URL/api/users/me/following/$TARGET_USER_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected success response shape:

```json
{
  "code": 0,
  "message": "",
  "data": {
    "user": {
      "id": 2,
      "nickname": "target nickname",
      "avatar": ""
    },
    "followed_at": "2026-05-25T12:00:00+08:00"
  }
}
```

Following the same user again is safe. The existing relation is returned.

```bash
curl -s -X POST "$BASE_URL/api/users/me/following/$TARGET_USER_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Follow yourself, expected to fail:

```bash
curl -s -X POST "$BASE_URL/api/users/me/following/$MY_USER_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected business error:

```json
{
  "code": 11202,
  "message": "can not follow yourself",
  "data": null
}
```

Follow missing user, expected to fail:

```bash
curl -s -X POST "$BASE_URL/api/users/me/following/999999/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected business error:

```json
{
  "code": 11201,
  "message": "user not found",
  "data": null
}
```

## List My Following

This endpoint is paginated.

```bash
curl -s -X GET "$BASE_URL/api/users/me/following/?page=1&page_size=16" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

## List My Followers

This endpoint is paginated.

```bash
curl -s -X GET "$BASE_URL/api/users/me/followers/?page=1&page_size=16" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

## Public User Following

This endpoint is paginated and does not require authentication.

```bash
curl -s -X GET "$BASE_URL/api/users/$MY_USER_ID/following/?page=1&page_size=16" | jq
```

Missing public user, expected to fail:

```bash
curl -s -X GET "$BASE_URL/api/users/999999/following/" | jq
```

Expected business error:

```json
{
  "code": 11201,
  "message": "user not found",
  "data": null
}
```

## Public User Followers

This endpoint is paginated and does not require authentication.

```bash
curl -s -X GET "$BASE_URL/api/users/$TARGET_USER_ID/followers/?page=1&page_size=16" | jq
```

Missing public user, expected to fail:

```bash
curl -s -X GET "$BASE_URL/api/users/999999/followers/" | jq
```

Expected business error:

```json
{
  "code": 11201,
  "message": "user not found",
  "data": null
}
```

## Unfollow User

```bash
curl -s -X DELETE "$BASE_URL/api/users/me/following/$TARGET_USER_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Unfollow the same user again, expected to fail:

```bash
curl -s -X DELETE "$BASE_URL/api/users/me/following/$TARGET_USER_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected business error:

```json
{
  "code": 11203,
  "message": "follow relation not found",
  "data": null
}
```

Unfollow missing user, expected to fail:

```bash
curl -s -X DELETE "$BASE_URL/api/users/me/following/999999/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected business error:

```json
{
  "code": 11201,
  "message": "user not found",
  "data": null
}
```

## Frontend Flow

On another user's profile page:

1. Render public profile data from `GET /api/users/{user_id}/profile/`.
2. Use the current user's known follow state if it is already loaded.
3. Follow with `POST /api/users/me/following/{target_user_id}/`.
4. Unfollow with `DELETE /api/users/me/following/{target_user_id}/`.
5. Refresh follower/following counts from profile or list endpoints after the write.
