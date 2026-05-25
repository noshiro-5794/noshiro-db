# Sync API

Run the common setup in [README](./README.md), then login with [Auth](./users-auth.md) as an admin user to set `ACCESS_TOKEN`.

Sync APIs are staff-only. A normal logged-in user receives a permission error and the frontend should hide sync buttons when `GET /api/users/me/profile/` returns `is_staff=false`.

## Resync One Subject

This endpoint resyncs one local subject by UUID:

- Subject base data.
- Episodes for this subject.
- Staff relations and staff detail data.
- Character relations, actor relations, character detail data, and actor staff detail data.
- Direct subject relations.

It intentionally does not fully sync related subjects from the subject relations list. Related subjects may be created as lightweight placeholders only when needed for relation foreign keys.

Default async request:

```bash
SUBJECT_ID="000212ed-b7b4-45c1-8d0d-7cd72906baa4"

curl -s -X POST "$BASE_URL/api/sync/subjects/$SUBJECT_ID/resync/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq
```

Expected response:

```json
{
  "code": 0,
  "message": "",
  "data": {
    "task_id": "celery-task-id",
    "status": "queued",
    "subject_id": "000212ed-b7b4-45c1-8d0d-7cd72906baa4"
  }
}
```

Synchronous request for local testing:

```bash
curl -s -X POST "$BASE_URL/api/sync/subjects/$SUBJECT_ID/resync/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"run_async": false}' | jq
```

Expected synchronous response shape:

```json
{
  "code": 0,
  "message": "",
  "data": {
    "subject_id": "000212ed-b7b4-45c1-8d0d-7cd72906baa4",
    "bangumi_id": 123,
    "title": "title",
    "subject_type": "anime",
    "episode_synced": true,
    "staff_count": 0,
    "character_count": 0,
    "related_subject_count": 0
  }
}
```

Non-admin request, expected to fail:

```bash
curl -s -X POST "$BASE_URL/api/sync/subjects/$SUBJECT_ID/resync/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq
```

## Management Command

Sync by local UUID:

```bash
./venv/bin/python manage.py sync_subject --uuid "$SUBJECT_ID"
```

Sync by Bangumi subject ID:

```bash
./venv/bin/python manage.py sync_subject --bangumi-id 123
```

## Incremental Sync Status

This API is staff-only.

```bash
curl -s -X GET "$BASE_URL/api/sync/incremental/status/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected response shape:

```json
{
  "code": 0,
  "message": "",
  "data": {
    "tasks": [
      {
        "task_name": "incremental_subject",
        "shard": "main",
        "current_id": 640000,
        "end_id": 640000,
        "status": "idle",
        "fail_count": 0,
        "updated_at": "2026-05-25T00:00:00+08:00"
      }
    ]
  }
}
```

## Run Incremental Sync

Default async request. This runs all incremental phases in the same order as full sync:

```text
incremental_subject
incremental_episode
incremental_subject_subject_relation
incremental_subject_staff_relation
incremental_subject_character_relation
incremental_character
incremental_staff
```

```bash
curl -s -X POST "$BASE_URL/api/sync/incremental/run/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq
```

Override one window size:

```bash
curl -s -X POST "$BASE_URL/api/sync/incremental/run/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 100}' | jq
```

Run one phase only:

```bash
curl -s -X POST "$BASE_URL/api/sync/incremental/run/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_name": "incremental_subject", "batch_size": 100}' | jq
```

Synchronous request for local testing:

```bash
curl -s -X POST "$BASE_URL/api/sync/incremental/run/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"run_async": false, "batch_size": 10}' | jq
```

Expected synchronous response shape:

```json
{
  "code": 0,
  "message": "",
  "data": {
    "results": [
      {
        "task_name": "incremental_subject",
        "shard": "main",
        "start_id": 640001,
        "end_id": 640010,
        "processed_count": 10,
        "synced_count": 0,
        "skipped_count": 10,
        "failed_count": 0
      }
    ]
  }
}
```

## Incremental Management Command

Show status:

```bash
./venv/bin/python manage.py incremental_sync --status
```

Run one window with configured batch size:

```bash
./venv/bin/python manage.py incremental_sync
```

Run a small local test window:

```bash
./venv/bin/python manage.py incremental_sync --batch-size 10
```

Run one phase only:

```bash
./venv/bin/python manage.py incremental_sync --task incremental_subject --batch-size 10
```

## Incremental Schedule

Celery Beat runs `apps.sync.tasks.incremental.run_incremental_sync_task` every day at `04:00` by default. It runs all incremental phases unless a specific `task_name` is passed.

Environment variables:

```text
SYNC_INCREMENTAL_SUBJECT_BATCH_SIZE=1000
SYNC_INCREMENTAL_MAX_CONSECUTIVE_ERRORS=20
SYNC_INCREMENTAL_MAX_CONSECUTIVE_SKIPS=50
SYNC_INCREMENTAL_CRON_HOUR=4
SYNC_INCREMENTAL_CRON_MINUTE=0
```

Incremental cursors are initialized from the largest successfully synced source ID, not from the full sync scan upper bound. This avoids missing new Bangumi IDs when a full sync intentionally scanned beyond Bangumi's actual maximum ID at that time.

When a phase sees too many consecutive 404/missing IDs, it treats that as reaching the current Bangumi frontier and keeps the cursor at the last successfully synced ID.

## Calendar Sync

Sync Bangumi daily broadcast calendar and fully resync every subject currently in that calendar.

Manual command:

```bash
./venv/bin/python manage.py sync_calendar
```

Only sync calendar entries and subject base data:

```bash
./venv/bin/python manage.py sync_calendar --skip-subject-details
```

Admin API, async by default:

```bash
curl -s -X POST "$BASE_URL/api/sync/calendar/run/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq
```

Synchronous local test:

```bash
curl -s -X POST "$BASE_URL/api/sync/calendar/run/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"run_async": false, "sync_subject_details": false}' | jq
```

Celery Beat runs `apps.sync.tasks.calendar.sync_calendar_task` every day at `03:30` by default.

Environment variables:

```text
SYNC_CALENDAR_CRON_HOUR=3
SYNC_CALENDAR_CRON_MINUTE=30
```
