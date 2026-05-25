# API Documentation

Frontend-facing API command documentation lives in this directory.

## Common Setup

```bash
BASE_URL="http://127.0.0.1:8008"
COOKIE_JAR="/tmp/noshiro_api_cookies.txt"
EMAIL="user@example.com"
PASSWORD="TestPass123!"
NEW_PASSWORD="NewPass456!"

rm -f "$COOKIE_JAR"
```

Authenticated APIs use:

```bash
-H "Authorization: Bearer $ACCESS_TOKEN"
```

Refresh-cookie APIs use:

```bash
-b "$COOKIE_JAR" -c "$COOKIE_JAR"
```

## Paginated Response

Paginated APIs use the same top-level response envelope as other APIs:

```json
{
  "code": 0,
  "message": "",
  "data": {
    "count": 0,
    "next": null,
    "previous": null,
    "results": []
  }
}
```

Supported query params:

```text
page=1
page_size=16
```

`page_size` is capped at `64`.

## Modules

### Users

- [Auth](./users-auth.md): register, login, refresh, logout, reset password.
- [Profile](./users-profile.md): profile read/update and avatar upload.
- [User Subjects](./users-subjects.md): list, create, update, delete user subject records.
- [Episode Progress](./users-progress.md): read and update per-episode watch progress.
- [Tags](./users-tags.md): manage user tags and bind tags to marked subjects.
- [Rating Details](./users-rating-details.md): replace and read detailed rating dimensions.
- [Reviews](./users-reviews.md): create, list, update, and delete user reviews.
- [Collections](./users-collections.md): create collections and manage marked subject items.
- [Follows](./users-follows.md): follow users and list following/follower relations.
- [Public User Profiles](./users-public-profiles.md): public profile, subjects, reviews, and collections.
- [Activities And Feed](./users-activities.md): user activities, public activities, and following feed.

### Index

- [Index Subjects](./index-subjects.md): public subject search, filtering, and detail.

## Frontend Auth Notes

The backend uses a short-lived access token plus a long-lived HttpOnly refresh cookie.

Login/register responses return only:

```json
{
  "access": "access_token_here"
}
```

The refresh token is set in an HttpOnly cookie named `noshiro_refresh`.

Browser requests that need refresh-cookie behavior must include:

```js
credentials: "include"
```

Example:

```js
await fetch(`${baseUrl}/api/users/token/refresh/`, {
  method: "POST",
  credentials: "include",
});
```

For production:

- Set `JWT_REFRESH_COOKIE_SECURE=True`.
- Use explicit `CORS_ALLOWED_ORIGINS`.
- Avoid `CORS_ALLOW_ALL_ORIGINS=True`.
- Keep refresh token in HttpOnly cookie, not localStorage.
