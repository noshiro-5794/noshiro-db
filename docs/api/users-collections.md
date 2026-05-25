# Collections API

Run the common setup in [README](./README.md), then login with [Auth](./auth.md) to set `ACCESS_TOKEN`.

## Setup

Use subjects that have already been marked by the current user.

```bash
SUBJECT_ID_1="000212ed-b7b4-45c1-8d0d-7cd72906baa4"
SUBJECT_ID_2="0001c709-8c55-4ebe-8bd3-f2c269949dcb"
```

Important ID distinction:

- `collection_id` is the current user's collection resource ID.
- `item_id` is the collection item resource ID.
- `subject_id` is the global subject UUID.
- New subject detail pages should add items by `subject_id`.
- `user_subject_id` item writes are kept for compatibility with older screens.

## List My Collections

This endpoint is paginated.

```bash
curl -s -X GET "$BASE_URL/api/users/me/collections/?page=1&page_size=16" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Search by collection name:

```bash
curl -s -X GET "$BASE_URL/api/users/me/collections/?keyword=favorites&page=1&page_size=16" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Ordering:

```bash
curl -s -X GET "$BASE_URL/api/users/me/collections/?ordering=-item_count" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
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

## Create Collection

```bash
COLLECTION_ID=$(
  curl -s -X POST "$BASE_URL/api/users/me/collections/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "Favorites",
      "simple_rating": 5,
      "note": "My favorite subjects.",
      "is_public": true
    }' | tee /tmp/noshiro_create_collection.json | jq -r ".data.id // empty"
)

cat /tmp/noshiro_create_collection.json | jq
echo "$COLLECTION_ID"
```

Blank name, expected to fail validation:

```bash
curl -s -X POST "$BASE_URL/api/users/me/collections/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": " "
  }' | jq
```

## Get Collection Detail

```bash
curl -s -X GET "$BASE_URL/api/users/me/collections/$COLLECTION_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Missing collection, expected to fail:

```bash
curl -s -X GET "$BASE_URL/api/users/me/collections/999999/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected business error:

```json
{
  "code": 12400,
  "message": "collection not found",
  "data": null
}
```

## Update Collection

```bash
curl -s -X PATCH "$BASE_URL/api/users/me/collections/$COLLECTION_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Favorites Updated",
    "simple_rating": 4,
    "note": "Updated note.",
    "is_public": false
  }' | jq
```

Partial update:

```bash
curl -s -X PATCH "$BASE_URL/api/users/me/collections/$COLLECTION_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "note": "Only note changed."
  }' | jq
```

## List Collection Items

This endpoint is paginated.

```bash
curl -s -X GET "$BASE_URL/api/users/me/collections/$COLLECTION_ID/items/?page=1&page_size=16" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

## Add Collection Item By Subject

Recommended subject-scoped write:

```bash
ITEM_ID=$(
  curl -s -X POST "$BASE_URL/api/users/me/collections/$COLLECTION_ID/items/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"subject_id\": \"$SUBJECT_ID_1\",
      \"order\": 1,
      \"relation\": \"main\"
    }" | tee /tmp/noshiro_add_collection_item.json | jq -r ".data.id // empty"
)

cat /tmp/noshiro_add_collection_item.json | jq
echo "$ITEM_ID"
```

Adding the same subject again updates the existing item and returns the same `item_id`:

```bash
curl -s -X POST "$BASE_URL/api/users/me/collections/$COLLECTION_ID/items/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"subject_id\": \"$SUBJECT_ID_1\",
    \"order\": 2,
    \"relation\": \"updated relation\"
  }" | jq
```

Unmarked subject, expected to fail:

```bash
UNMARKED_SUBJECT_ID="00000000-0000-0000-0000-000000000000"

curl -s -X POST "$BASE_URL/api/users/me/collections/$COLLECTION_ID/items/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"subject_id\": \"$UNMARKED_SUBJECT_ID\"
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

Both IDs or no ID, expected to fail validation:

```bash
curl -s -X POST "$BASE_URL/api/users/me/collections/$COLLECTION_ID/items/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order": 1
  }' | jq
```

## Replace Collection Items

This replaces the full item set for the collection.

```bash
curl -s -X PUT "$BASE_URL/api/users/me/collections/$COLLECTION_ID/items/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"items\": [
      {
        \"subject_id\": \"$SUBJECT_ID_1\",
        \"order\": 1,
        \"relation\": \"main\"
      },
      {
        \"subject_id\": \"$SUBJECT_ID_2\",
        \"order\": 2,
        \"relation\": \"related\"
      }
    ]
  }" | jq
```

Duplicate resolved subjects, expected to fail:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/collections/$COLLECTION_ID/items/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"items\": [
      {
        \"subject_id\": \"$SUBJECT_ID_1\"
      },
      {
        \"subject_id\": \"$SUBJECT_ID_1\"
      }
    ]
  }" | jq
```

Expected business error:

```json
{
  "code": 12402,
  "message": "invalid user subject ids",
  "data": null
}
```

Clear collection items:

```bash
curl -s -X PUT "$BASE_URL/api/users/me/collections/$COLLECTION_ID/items/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "items": []
  }' | jq
```

Add one item again for the delete test:

```bash
ITEM_ID=$(
  curl -s -X POST "$BASE_URL/api/users/me/collections/$COLLECTION_ID/items/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"subject_id\": \"$SUBJECT_ID_1\",
      \"order\": 1,
      \"relation\": \"delete test\"
    }" | tee /tmp/noshiro_add_collection_item_again.json | jq -r ".data.id // empty"
)

cat /tmp/noshiro_add_collection_item_again.json | jq
echo "$ITEM_ID"
```

## Compatibility Item Write

Older screens can still add by `user_subject_id`.

```bash
USER_SUBJECT_ID=1

curl -s -X POST "$BASE_URL/api/users/me/collections/$COLLECTION_ID/items/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_subject_id\": $USER_SUBJECT_ID,
    \"order\": 1,
    \"relation\": \"legacy write\"
  }" | jq
```

Invalid `user_subject_id`, expected to fail:

```bash
curl -s -X POST "$BASE_URL/api/users/me/collections/$COLLECTION_ID/items/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_subject_id": 999999
  }' | jq
```

Expected business error:

```json
{
  "code": 12100,
  "message": "user subject not found",
  "data": null
}
```

## Delete Collection Item

```bash
curl -s -X DELETE "$BASE_URL/api/users/me/collections/$COLLECTION_ID/items/$ITEM_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Delete missing item, expected to fail:

```bash
curl -s -X DELETE "$BASE_URL/api/users/me/collections/$COLLECTION_ID/items/999999/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected business error:

```json
{
  "code": 12401,
  "message": "collection item not found",
  "data": null
}
```

## Delete Collection

```bash
curl -s -X DELETE "$BASE_URL/api/users/me/collections/$COLLECTION_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Get deleted collection, expected to fail:

```bash
curl -s -X GET "$BASE_URL/api/users/me/collections/$COLLECTION_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

## Frontend Flow

On a subject detail page:

1. Load subject context with `GET /api/users/me/subjects/{subject_id}/context/`.
2. If `data.is_marked` is false, ask the user to mark the subject first.
3. Let the user choose or create a collection.
4. Add the subject with `POST /api/users/me/collections/{collection_id}/items/` and body `{ "subject_id": subjectId }`.

The frontend does not need to know or expose `user_subject_id` for this flow.
