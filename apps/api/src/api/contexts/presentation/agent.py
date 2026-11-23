"""Generate grounded work metadata from the permitted evidence bundle."""

from __future__ import annotations

from typing import Any

from api.shared.ai import complete_json

from .display import DisplayProposal
from .rules import propose

SYSTEM_PROMPT = """\
You decide what a catalogue page shows for one work. Reply with JSON only:
{
  "title_name_id": <id of one name from the bundle>,
  "description": "<2-4 sentences>",
  "description_source_ids": [<ids of the descriptions you used>],
  "cover_asset_id": <id of one cover from the bundle, or null>
}

Rules:
- Cite only ids that appear in the bundle.
- You may rewrite the description, but every number or date you state must appear
  in a cited description.
- Write in the requested language; if it is empty, write in the language of the
  descriptions you cite.
- Do not invent facts. If the bundle does not support a detail, leave it out.
"""


def _bundle_for_prompt(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "language": bundle["language"],
        "entity": bundle["entity"],
        "names": bundle["names"],
        "descriptions": bundle["descriptions"],
        "media": bundle["media"],
    }


async def propose_with_model(
    bundle: dict[str, Any],
) -> tuple[DisplayProposal, dict[str, Any]]:
    if not bundle.get("ai_evidence") or bundle["entity"]["entity_type"] != "work":
        raise ValueError("A work bundle filtered for AI use is required.")
    base = propose(bundle)
    result, usage = await complete_json(system=SYSTEM_PROMPT, payload=_bundle_for_prompt(bundle))
    proposal = DisplayProposal(
        title_name_id=int(result.get("title_name_id", base.title_name_id)),
        description_text=str(result.get("description", "")),
        description_source_ids=[int(value) for value in result.get("description_source_ids", [])],
        cover_asset_id=(str(result["cover_asset_id"]) if result.get("cover_asset_id") else None),
        is_machine_generated=True,
        confidence=None,
    )
    return proposal, usage
