from django.db.models import (
    Count,
    FloatField,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce, Greatest
from django.contrib.postgres.search import TrigramSimilarity

from apps.index.constants import PRIMARY_SUBJECT_TYPES
from apps.index.exceptions import SubjectNotFound
from apps.index.models import (
    Episode,
    Subject,
    SubjectCharacterRelation,
    SubjectStaffRelation,
)


class SubjectSelector:

    @staticmethod
    def base_queryset():
        return Subject.objects.all()

    @staticmethod
    def with_section_counts(qs):
        return qs.annotate(
            episode_count=Coalesce(
                Subquery(
                    Episode.objects.filter(subject_id=OuterRef("pk"))
                    .order_by()
                    .values("subject_id")
                    .annotate(count=Count("id"))
                    .values("count")[:1],
                    output_field=IntegerField(),
                ),
                Value(0),
            ),
            staff_count=Coalesce(
                Subquery(
                    SubjectStaffRelation.objects.filter(subject_id=OuterRef("pk"))
                    .order_by()
                    .values("subject_id")
                    .annotate(count=Count("id"))
                    .values("count")[:1],
                    output_field=IntegerField(),
                ),
                Value(0),
            ),
            character_count=Coalesce(
                Subquery(
                    SubjectCharacterRelation.objects.filter(subject_id=OuterRef("pk"))
                    .order_by()
                    .values("subject_id")
                    .annotate(count=Count("id"))
                    .values("count")[:1],
                    output_field=IntegerField(),
                ),
                Value(0),
            ),
        )

    @classmethod
    def list_subjects(
        cls,
        *,
        keyword=None,
        subject_type=None,
        nsfw=None,
        ordering="-updated_at",
    ):
        qs = cls.base_queryset().filter(subject_type__in=PRIMARY_SUBJECT_TYPES)

        if subject_type:
            qs = qs.filter(subject_type=subject_type)

        if nsfw is not None:
            qs = qs.filter(nsfw=nsfw)

        if keyword:
            keyword = keyword.strip()
            if keyword:
                qs = cls.apply_keyword_search(qs, keyword=keyword)
                return qs.order_by("-search_score", "-updated_at", "-id")

        allowed_ordering = {
            "date",
            "-date",
            "title",
            "-title",
            "updated_at",
            "-updated_at",
            "created_at",
            "-created_at",
        }

        if ordering not in allowed_ordering:
            ordering = "-updated_at"

        return qs.order_by(ordering, "-id")

    @staticmethod
    def apply_keyword_search(qs, *, keyword: str):
        zero = Value(0.0, output_field=FloatField())

        qs = qs.annotate(
            title_similarity=Coalesce(TrigramSimilarity("title", keyword), zero),
            title_cn_similarity=Coalesce(
                TrigramSimilarity("title_cn", keyword),
                zero,
            ),
        ).annotate(
            search_score=Greatest("title_similarity", "title_cn_similarity")
        )

        return qs.filter(
            Q(title__icontains=keyword)
            | Q(title_cn__icontains=keyword)
            | Q(search_score__gte=0.15)
        )

    @classmethod
    def get_subject_or_raise(cls, *, subject_id):
        try:
            return cls.with_section_counts(cls.base_queryset()).get(id=subject_id)
        except Subject.DoesNotExist:
            raise SubjectNotFound()

    @staticmethod
    def get_subject_reference_or_raise(*, subject_id):
        try:
            return Subject.objects.only("id").get(id=subject_id)
        except Subject.DoesNotExist:
            raise SubjectNotFound()
