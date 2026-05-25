# Auth API

Run the common setup in [README](./README.md) first.

## Send Verification Code

Register:

```bash
curl -s -X POST "$BASE_URL/api/users/send-code/" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"purpose\": \"register\"
  }" | jq
```

Login:

```bash
curl -s -X POST "$BASE_URL/api/users/send-code/" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"purpose\": \"login\"
  }" | jq
```

Reset password:

```bash
curl -s -X POST "$BASE_URL/api/users/send-code/" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"purpose\": \"reset_password\"
  }" | jq
```

## Register

Replace `123456` with the real email code.

```bash
ACCESS_TOKEN=$(
  curl -s -c "$COOKIE_JAR" -X POST "$BASE_URL/api/users/register/" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"$EMAIL\",
      \"password\": \"$PASSWORD\",
      \"nickname\": \"harry\",
      \"code\": \"123456\"
    }" | tee /tmp/noshiro_register_response.json | jq -r ".data.access // empty"
)

cat /tmp/noshiro_register_response.json | jq
echo "$ACCESS_TOKEN"
cat "$COOKIE_JAR"
```

## Password Login

Login returns an access token in JSON and sets the refresh token in an HttpOnly cookie.

```bash
ACCESS_TOKEN=$(
  curl -s -c "$COOKIE_JAR" -X POST "$BASE_URL/api/users/login/password/" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"$EMAIL\",
      \"password\": \"$PASSWORD\"
    }" | tee /tmp/noshiro_login_response.json | jq -r ".data.access"
)

cat /tmp/noshiro_login_response.json | jq
echo "$ACCESS_TOKEN"
cat "$COOKIE_JAR"
```

## Email Code Login

Replace `654321` with the real email code.

```bash
ACCESS_TOKEN=$(
  curl -s -c "$COOKIE_JAR" -X POST "$BASE_URL/api/users/login/code/" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"$EMAIL\",
      \"code\": \"654321\"
    }" | tee /tmp/noshiro_code_login_response.json | jq -r ".data.access // empty"
)

cat /tmp/noshiro_code_login_response.json | jq
echo "$ACCESS_TOKEN"
cat "$COOKIE_JAR"
```

## Refresh Access Token

No refresh token is sent in the request body. The backend reads the HttpOnly refresh cookie.

```bash
ACCESS_TOKEN=$(
  curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -X POST "$BASE_URL/api/users/token/refresh/" \
    | tee /tmp/noshiro_refresh_response.json | jq -r ".data.access // empty"
)

cat /tmp/noshiro_refresh_response.json | jq
echo "$ACCESS_TOKEN"
cat "$COOKIE_JAR"
```

## Logout

Logout blacklists the current refresh token and clears the refresh cookie.

```bash
curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -X POST "$BASE_URL/api/users/logout/" | jq
cat "$COOKIE_JAR"
```

Refresh after logout should fail:

```bash
curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -X POST "$BASE_URL/api/users/token/refresh/" | jq
```

## Reset Password

Replace `987654` with the real email code.

```bash
curl -s -X POST "$BASE_URL/api/users/password/reset/" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"code\": \"987654\",
    \"new_password\": \"$NEW_PASSWORD\"
  }" | jq
```
