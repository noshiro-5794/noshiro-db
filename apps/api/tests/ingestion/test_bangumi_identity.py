import pytest

from api.contexts.identity.relations import canonical_relation_type
from api.contexts.identity.roles import role_key, role_label
from api.contexts.identity.vndb import extract_ids
from api.contexts.synchronization.terms import normalize_key


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"infobox": [{"key": "VNDB", "value": "V17"}]}, {("v17", "/infobox/0/value")}),
        ({"url": "https://www.vndb.org/v17/characters"}, {("v17", "/url")}),
        ({"name": "Novel", "id": "v17"}, set()),
        ({"url": "https://vndb.org.example.test/v17"}, set()),
        ({"url": "http://["}, set()),
        ({"vndb/link~": ["v17"]}, {("v17", "/vndb~1link~0/0")}),
    ],
)
def test_explicit_source_ids_keep_real_json_pointers(payload, expected):
    assert set(extract_ids(payload)) == expected


def test_reviewed_alias_keys_match_unicode_normalization_and_lowercase():
    assert normalize_key("  \uff33\uff26   Straße ") == "sf straße"


def test_credit_and_relation_terminology_is_language_independent():
    assert {role_key(role) for role in ("导演", "監督", "Director")} == {"director"}
    assert [role_label("監督", language) for language in ("zh-CN", "ja-JP", "en-US")] == [
        "导演",
        "監督",
        "Director",
    ]
    assert role_label("Animation Director (OP, ep 1)", "ja-JP") == "作画監督 (OP, ep 1)"
    assert role_label("ADR Director (English)", "zh-CN") == "ADR Director (English)"
    assert {canonical_relation_type(role) for role in ("续作", "続編", "SEQUEL")} == {"sequel"}
