from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.core.pagination import DefaultPageNumberPagination
from apps.core.response import success_response
from apps.index.api.serializers.subject_section_serializer import (
    SubjectCharacterResponseSerializer,
    SubjectEpisodeResponseSerializer,
    SubjectRelationListResponseSerializer,
    SubjectStaffResponseSerializer,
)
from apps.index.selectors.subject_section_selector import SubjectSectionSelector


class SubjectEpisodePagination(DefaultPageNumberPagination):

    page_size = 96
    max_page_size = 96


class SubjectEpisodeListView(APIView):

    permission_classes = [AllowAny]

    def get(self, request, subject_id):
        qs = SubjectSectionSelector.list_subject_episodes(subject_id=subject_id)

        paginator = SubjectEpisodePagination()
        page = paginator.paginate_queryset(qs, request, view=self)

        serializer = SubjectEpisodeResponseSerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(serializer.data)


class SubjectStaffListView(APIView):

    permission_classes = [AllowAny]

    def get(self, request, subject_id):
        qs = SubjectSectionSelector.list_subject_staff(subject_id=subject_id)

        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(qs, request, view=self)

        serializer = SubjectStaffResponseSerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(serializer.data)


class SubjectCharacterListView(APIView):

    permission_classes = [AllowAny]

    def get(self, request, subject_id):
        qs = SubjectSectionSelector.list_subject_characters(subject_id=subject_id)

        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(qs, request, view=self)

        serializer = SubjectCharacterResponseSerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(serializer.data)


class SubjectRelationListView(APIView):

    permission_classes = [AllowAny]

    def get(self, request, subject_id):
        outgoing, incoming = SubjectSectionSelector.list_subject_relations(
            subject_id=subject_id,
        )

        serializer = SubjectRelationListResponseSerializer(
            {
                "outgoing": outgoing,
                "incoming": incoming,
            }
        )

        return success_response(data=serializer.data)
