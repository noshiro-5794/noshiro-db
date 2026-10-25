"""Another account's public profile: who they are and what they have shared."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from api.contexts.access.dependencies import optional_user
from api.contexts.presentation.fragments import fetch
from api.db import SessionDep
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/users", tags=["profile"])

NOT_FOUND = "User not found."


@router.get("/{user_id}/")
async def public_profile(
    user_id: int,
    session: SessionDep,
    viewer: Annotated[Any | None, Depends(optional_user)],
) -> dict[str, Any]:
    if viewer is not None and viewer.id != user_id:
        blocked = await fetch(
            session,
            "SELECT 1 FROM community_user_block"
            " WHERE (user_id = :a AND blocked_user_id = :b)"
            "    OR (user_id = :b AND blocked_user_id = :a)",
            {"a": viewer.id, "b": user_id},
        )
        if blocked:
            raise ProblemError(status_code=404, detail=NOT_FOUND)
    rows = await fetch(
        session,
        """
        SELECT person.id, person.email,
               profile.nickname, profile.avatar, profile.bio,
               (SELECT count(*) FROM user_library_entry WHERE user_id = person.id
                 AND entity_id IS NOT NULL AND is_public) AS library_entry_count,
               (SELECT count(*) FROM user_review AS review
                  JOIN user_library_entry AS entry
                    ON entry.id = review.user_subject_id
                 WHERE entry.user_id = person.id AND entry.entity_id IS NOT NULL
                   AND entry.is_public AND review.is_public) AS review_count,
               (SELECT count(*) FROM user_collection WHERE user_id = person.id
                 AND is_public) AS collection_count,
               (SELECT count(*) FROM community_user_follow WHERE follower_id = person.id)
                 AS following_count,
               (SELECT count(*) FROM community_user_follow WHERE following_id = person.id)
                 AS follower_count,
               EXISTS (SELECT 1 FROM community_user_follow
                        WHERE follower_id = :viewer AND following_id = person.id)
                 AS is_following
        FROM "user" AS person
        LEFT JOIN user_profile AS profile ON profile.user_id = person.id
        WHERE person.id = :user_id
        """,
        {"user_id": user_id, "viewer": viewer.id if viewer else 0},
    )
    if not rows:
        raise ProblemError(status_code=404, detail=NOT_FOUND)
    row = rows[0]
    return {
        "id": row.id,
        "nickname": row.nickname or "",
        "avatar": row.avatar or "",
        "bio": row.bio or "",
        "stats": {
            "library_entry_count": int(row.library_entry_count),
            "review_count": int(row.review_count),
            "collection_count": int(row.collection_count),
            "following_count": int(row.following_count),
            "follower_count": int(row.follower_count),
        },
        "is_following": bool(row.is_following),
    }
