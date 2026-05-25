from rest_framework import serializers


def subject_summary(subject):
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


class SubjectEpisodeResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    type = serializers.CharField()
    ep_num = serializers.IntegerField(allow_null=True)
    sort = serializers.IntegerField(allow_null=True)
    date = serializers.DateField(allow_null=True)
    description = serializers.CharField()


class SubjectStaffResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="staff.id")
    name = serializers.CharField(source="staff.name")
    role = serializers.CharField()
    image_thumbnail = serializers.CharField(source="staff.image_thumbnail")
    type = serializers.CharField(source="staff.type")


class SubjectCharacterResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="character.id")
    name = serializers.CharField(source="character.name")
    role = serializers.CharField()
    image_thumbnail = serializers.CharField(source="character.image_thumbnail")
    type = serializers.CharField(source="character.type")


class SubjectRelationListResponseSerializer(serializers.Serializer):
    outgoing = serializers.SerializerMethodField()
    incoming = serializers.SerializerMethodField()

    def get_outgoing(self, obj):
        return [
            {
                "direction": "outgoing",
                "relation": relation.relation,
                "subject": subject_summary(relation.target),
            }
            for relation in obj["outgoing"]
        ]

    def get_incoming(self, obj):
        return [
            {
                "direction": "incoming",
                "relation": relation.relation,
                "subject": subject_summary(relation.source),
            }
            for relation in obj["incoming"]
        ]
