from rest_framework import serializers

from apps.index.constants import PRIMARY_SUBJECT_TYPES
from apps.index.models import Subject


class SubjectListQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    subject_type = serializers.ChoiceField(
        required=False,
        choices=[
            (subject_type, Subject.SubjectType(subject_type).label)
            for subject_type in PRIMARY_SUBJECT_TYPES
        ],
    )
    nsfw = serializers.BooleanField(required=False)
    ordering = serializers.ChoiceField(
        required=False,
        choices=[
            "date",
            "-date",
            "title",
            "-title",
            "updated_at",
            "-updated_at",
            "created_at",
            "-created_at",
        ],
    )


class SubjectListResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = [
            "id",
            "subject_type",
            "title",
            "title_cn",
            "date",
            "image_thumbnail",
            "platform",
            "nsfw",
            "series",
            "volumes",
            "eps",
            "total_episodes",
        ]


class SubjectDetailResponseSerializer(SubjectListResponseSerializer):
    episode_count = serializers.IntegerField(read_only=True)
    staff_count = serializers.IntegerField(read_only=True)
    character_count = serializers.IntegerField(read_only=True)
    image_original = serializers.URLField()
    description = serializers.CharField()
    infobox = serializers.JSONField()
    tags = serializers.JSONField()

    class Meta(SubjectListResponseSerializer.Meta):
        fields = SubjectListResponseSerializer.Meta.fields + [
            "image_original",
            "description",
            "infobox",
            "tags",
            "episode_count",
            "staff_count",
            "character_count",
        ]
