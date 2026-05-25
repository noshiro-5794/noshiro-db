# Profile API

Run the common setup in [README](./README.md), then login with [Auth](./users-auth.md) to set `ACCESS_TOKEN`.

## Get My Profile

Unauthenticated request, expected to fail:

```bash
curl -s -X GET "$BASE_URL/api/users/me/profile/" | jq
```

Authenticated request:

```bash
curl -s -X GET "$BASE_URL/api/users/me/profile/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

The response includes `is_staff` and `is_superuser`, which the frontend can use to hide admin-only actions such as manual sync.

## Update My Profile

```bash
curl -s -X PATCH "$BASE_URL/api/users/me/profile/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nickname": "JRH",
    "bio": "my bio",
    "theme_color": "#66ccff"
  }' | jq
```

Empty body, expected to fail validation:

```bash
curl -s -X PATCH "$BASE_URL/api/users/me/profile/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq
```

## Upload Avatar

```bash
curl -s -X POST "$BASE_URL/api/users/me/avatar/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "avatar=@avatar.jpg" | jq
```

The returned URL uses the public MinIO domain:

```text
https://avatar.noshiro.moe/noshiro-avatars/avatars/{user_id}/{uuid}.jpg
```
