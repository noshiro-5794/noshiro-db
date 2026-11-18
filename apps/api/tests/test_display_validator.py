from typing import Any

from api.contexts.presentation.display import DisplayProposal, validate
from api.contexts.presentation.rules import propose


def bundle() -> dict[str, Any]:
    return {
        "bundle_version": "v1",
        "language": "",
        "entity": {"id": "e-1", "entity_type": "work", "audience": "general", "work_type": "anime"},
        "names": [
            {
                "id": 1,
                "text": "Original",
                "language": "ja",
                "script": "Jpan",
                "kind": "original",
                "is_official": True,
                "is_original": True,
            },
            {
                "id": 2,
                "text": "Alias",
                "language": "en",
                "script": "Latn",
                "kind": "alias",
                "is_official": False,
                "is_original": False,
            },
        ],
        "descriptions": [
            {"id": 10, "language": "ja", "text": "26話のアニメ。", "is_official": True},
        ],
        "fields": [
            {
                "predicate": "episode-count",
                "language": "",
                "fact_id": "f-1",
                "value": 26,
                "confidence": 0.9,
                "alternates": [],
            },
        ],
        "credits": [],
        "relations": [],
        "media": [
            {"asset_id": "a-1", "url": "https://x/1.jpg", "purpose": "cover", "safety": "safe"}
        ],
    }


def test_rule_proposal_is_valid() -> None:
    data = bundle()
    assert validate(data, propose(data)) == []


def test_unknown_title_is_rejected() -> None:
    errors = validate(bundle(), DisplayProposal(title_name_id=999))
    assert any("title_name_id" in error for error in errors)


def test_description_citing_unknown_row_is_rejected() -> None:
    errors = validate(
        bundle(),
        DisplayProposal(title_name_id=1, description_text="x", description_source_ids=[404]),
    )
    assert any("unknown rows" in error for error in errors)


def test_description_may_not_introduce_a_number() -> None:
    errors = validate(
        bundle(),
        DisplayProposal(
            title_name_id=1, description_text="A 99 episode series.", description_source_ids=[10]
        ),
    )
    assert any("no fact supports" in error for error in errors)


def test_unknown_cover_is_rejected() -> None:
    errors = validate(bundle(), DisplayProposal(title_name_id=1, cover_asset_id=None))
    assert errors == []
    errors = validate(
        bundle(),
        DisplayProposal(title_name_id=1, cover_asset_id="00000000-0000-0000-0000-000000000000"),
    )
    assert any("cover_asset_id" in error for error in errors)
