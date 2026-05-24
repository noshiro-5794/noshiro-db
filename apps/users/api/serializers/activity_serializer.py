from rest_framework import serializers

from apps.users.models import Activity


class ActivityUserResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nickname = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    def get_nickname(self, obj):
        profile = getattr(obj, "profile", None)

        if not profile:
            return ""

        return getattr(profile, "nickname", "") or ""

    def get_avatar(self, obj):
        profile = getattr(obj, "profile", None)

        if not profile:
            return ""

        avatar = getattr(profile, "avatar", "")

        if not avatar:
            return ""

        if hasattr(avatar, "url"):
            return avatar.url

        return str(avatar)


class ActivitySubjectResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    subject_type = serializers.CharField()
    title = serializers.CharField()
    title_cn = serializers.CharField(allow_blank=True, required=False)
    date = serializers.CharField(allow_blank=True, required=False)
    image_thumbnail = serializers.CharField(allow_blank=True, required=False)
    platform = serializers.CharField(allow_blank=True, required=False)
    nsfw = serializers.BooleanField(required=False)


class ActivityResponseSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    target_user = serializers.SerializerMethodField()
    user_subject = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    review = serializers.SerializerMethodField()
    collection = serializers.SerializerMethodField()
    collection_item = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            "id",
            "activity_type",
            "user",
            "target_user",
            "user_subject",
            "subject",
            "review",
            "collection",
            "collection_item",
            "message",
            "is_public",
            "created_at",
        ]

    def get_user(self, obj):
        if not obj.user:
            return None

        return ActivityUserResponseSerializer(obj.user).data

    def get_target_user(self, obj):
        if not obj.target_user:
            return None

        return ActivityUserResponseSerializer(obj.target_user).data

    def get_user_subject(self, obj):
        user_subject = obj.user_subject

        if not user_subject:
            return None

        return {
            "id": user_subject.id,
            "status": user_subject.status,
            "simple_rating": user_subject.simple_rating,
            "rating": user_subject.rating,
            "comment": user_subject.comment,
            "watch_start_date": user_subject.watch_start_date,
            "watch_end_date": user_subject.watch_end_date,
            "is_public": user_subject.is_public,
        }

    def get_subject(self, obj):
        subject = None

        if obj.user_subject:
            subject = obj.user_subject.subject
        elif obj.collection_item and obj.collection_item.user_subject:
            subject = obj.collection_item.user_subject.subject
        elif obj.review and obj.review.user_subject:
            subject = obj.review.user_subject.subject

        if not subject:
            return None

        return {
            "id": subject.id,
            "subject_type": subject.subject_type,
            "title": subject.title,
            "title_cn": subject.title_cn,
            "date": subject.date,
            "image_thumbnail": subject.image_thumbnail,
            "platform": subject.platform,
            "nsfw": subject.nsfw,
        }

    def get_review(self, obj):
        review = obj.review

        if not review:
            return None

        return {
            "id": review.id,
            "title": review.title,
            "content": review.content,
            "is_public": review.is_public,
            "is_spoiler": review.is_spoiler,
            "created_at": review.created_at,
        }

    def get_collection(self, obj):
        collection = obj.collection

        if not collection:
            return None

        return {
            "id": collection.id,
            "name": collection.name,
            "simple_rating": collection.simple_rating,
            "note": collection.note,
            "is_public": collection.is_public,
        }

    def get_collection_item(self, obj):
        collection_item = obj.collection_item

        if not collection_item:
            return None

        return {
            "id": collection_item.id,
            "order": collection_item.order,
            "relation": collection_item.relation,
        }
