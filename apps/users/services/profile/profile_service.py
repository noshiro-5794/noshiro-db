from django.db import transaction

from apps.users.models import User, UserProfile
from apps.users.exceptions import AvatarUploadFailed
from apps.users.storage.minio_client import minio_client


class ProfileService:

    @classmethod
    @transaction.atomic
    def upload_avatar(cls, *, user: User, file_obj) -> str:
        profile = user.profile
        try:
            url = minio_client.upload_file(
                file_obj,
                folder=f"avatars/{user.id}",
            )
        except Exception as e:
            raise AvatarUploadFailed() from e
        profile.avatar = url
        profile.save(update_fields=["avatar"])
        return url

    @classmethod
    @transaction.atomic
    def update_profile(
        cls,
        *,
        user: User,
        nickname: str = None,
        bio: str = None,
        theme_color: str = None,
    ) -> UserProfile:
        profile = user.profile
        changed_fields = []
        if nickname is not None:
            profile.nickname = nickname
            changed_fields.append("nickname")
        if bio is not None:
            profile.bio = bio
            changed_fields.append("bio")
        if theme_color is not None:
            profile.theme_color = theme_color
            changed_fields.append("theme_color")
        if changed_fields:
            profile.save(update_fields=changed_fields)
        return profile
