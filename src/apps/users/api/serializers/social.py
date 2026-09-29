from rest_framework import serializers


class SocialAuthorizeSerializer(serializers.Serializer):
    authorize_url = serializers.URLField()


class SocialProviderSerializer(serializers.Serializer):
    provider = serializers.CharField()
    enabled = serializers.BooleanField()
    authorize_path = serializers.CharField(allow_blank=True)
