"""The rule-based generator: a proposal with no model behind it.

It exists to fill drafts without AI, and to be the baseline the model is compared
against. It never invents text: the description is copied from a cited row.
"""

from __future__ import annotations

from typing import Any

from .display import DisplayProposal


def propose(bundle: dict[str, Any]) -> DisplayProposal:
    names = bundle["names"]
    if not names:
        raise ValueError("entity has no names to choose a title from")
    language = bundle["language"] or ""
    preferred = [item for item in names if language and item["language"] == language]
    preferred = preferred or [item for item in names if item["is_original"]]
    preferred = preferred or names
    title = sorted(preferred, key=lambda item: (not item["is_official"], item["id"]))[0]

    descriptions = bundle["descriptions"]
    description = descriptions[0] if descriptions else None
    cover = bundle["media"][0]["asset_id"] if bundle["media"] else None
    return DisplayProposal(
        title_name_id=title["id"],
        description_text=description["text"] if description else "",
        description_source_ids=[description["id"]] if description else [],
        cover_asset_id=cover,
        field_choices=[
            {
                "field": item["predicate"],
                "fact_id": item["fact_id"],
                "chosen_value": item["value"],
                "alternates": item["alternates"],
            }
            for item in bundle["fields"]
        ],
        is_machine_generated=False,
    )
