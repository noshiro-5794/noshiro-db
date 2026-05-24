from django.db import transaction, IntegrityError

from apps.users.models import UserFollow
from apps.users.exceptions import CannotFollowSelf, FollowRelationNotFound
from apps.users.selectors.follow_selector import UserFollowSelector
from apps.users.services.social.activity_service import ActivityService


class UserFollowService:

    @staticmethod
    @transaction.atomic
    def follow_user(*, follower, target_user_id: int):
        following = UserFollowSelector.get_user_by_id_or_raise(
            user_id=target_user_id,
        )

        if follower.id == following.id:
            raise CannotFollowSelf()

        try:
            relation, created = UserFollow.objects.get_or_create(
                follower=follower,
                following=following,
            )
        except IntegrityError:
            relation = UserFollow.objects.get(
                follower=follower,
                following=following,
            )
            created = False

        if created:
            ActivityService.create_user_followed_activity(
                follower=follower,
                following=following,
            )

        return relation, created

    @staticmethod
    @transaction.atomic
    def unfollow_user(*, follower, target_user_id: int):
        following = UserFollowSelector.get_user_by_id_or_raise(
            user_id=target_user_id,
        )

        deleted_count, _ = UserFollow.objects.filter(
            follower=follower,
            following=following,
        ).delete()

        if deleted_count == 0:
            raise FollowRelationNotFound()
