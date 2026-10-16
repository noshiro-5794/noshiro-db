"""Migration ``index.0017`` has to unwind the legacy galgame schema.

0017 removes the legacy ``galgame`` primary key while ``galgame_genre_relation``
still holds a foreign key to it.  Django 6.0 stopped appending ``CASCADE`` to
``DROP COLUMN``, so the statement now fails on a fresh database unless the
incoming constraint is dropped first.  The test database is built from the
migration graph on every run, so reaching this point at all already exercises
that ordering; the assertions below pin the end state it has to leave behind.
"""

import pytest
from django.db import connection


@pytest.mark.django_db(transaction=True)
def test_migration_0017_drops_the_legacy_galgame_tables():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
            "AND tablename IN ('galgame', 'galgame_genre_relation')"
        )
        assert cursor.fetchall() == []
