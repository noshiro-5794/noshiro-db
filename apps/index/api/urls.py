from django.urls import path

from apps.index.api.views.subject_section_view import (
    SubjectCharacterListView,
    SubjectEpisodeListView,
    SubjectRelationListView,
    SubjectStaffListView,
)
from apps.index.api.views.subject_view import (
    SubjectDetailView,
    SubjectListView,
)


urlpatterns = [
    path(
        "subjects/",
        SubjectListView.as_view(),
        name="subject-list",
    ),
    path(
        "subjects/<uuid:subject_id>/",
        SubjectDetailView.as_view(),
        name="subject-detail",
    ),
    path(
        "subjects/<uuid:subject_id>/episodes/",
        SubjectEpisodeListView.as_view(),
        name="subject-episode-list",
    ),
    path(
        "subjects/<uuid:subject_id>/staff/",
        SubjectStaffListView.as_view(),
        name="subject-staff-list",
    ),
    path(
        "subjects/<uuid:subject_id>/characters/",
        SubjectCharacterListView.as_view(),
        name="subject-character-list",
    ),
    path(
        "subjects/<uuid:subject_id>/relations/",
        SubjectRelationListView.as_view(),
        name="subject-relation-list",
    ),
]
