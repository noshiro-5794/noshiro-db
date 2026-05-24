from rest_framework.views import APIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from apps.core.response import success_response
from apps.users.services.profile.profile_service import ProfileService
from apps.users.api.serializers.profile_serializer import (
    AvatarUploadRequestSerializer,
    UserProfileResponseSerializer,
    UserProfileUpdateRequestSerializer,
)


class MyProfileView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile

        serializer = UserProfileResponseSerializer(profile)

        return success_response(data=serializer.data)

    def patch(self, request):
        serializer = UserProfileUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = ProfileService.update_profile(
            user=request.user,
            **serializer.validated_data,
        )

        output_serializer = UserProfileResponseSerializer(profile)

        return success_response(data=output_serializer.data)


class MyAvatarUploadView(APIView):

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = AvatarUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = ProfileService.upload_avatar(
            user=request.user,
            file_obj=serializer.validated_data["avatar"],
        )

        return success_response(data={"avatar": url})
