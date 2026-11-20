"""Reviewed term aliases used when projecting source metadata."""

import re
import unicodedata

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch


def normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).strip().lower())


async def preferred_terms(session: AsyncSession, values: list[str]) -> dict[str, str]:
    originals = {value.strip() for value in values if value.strip()}
    if not originals:
        return {}
    rows = await fetch(
        session,
        """
        SELECT DISTINCT ON (normalized_key) normalized_key, preferred_term
        FROM index_term_alias WHERE vocabulary='legacy' AND language=''
          AND provider_namespace_id IS NULL AND is_reviewed
          AND normalized_key=ANY(:keys)
        ORDER BY normalized_key, confidence DESC, id
        """,
        {"keys": sorted({normalize_key(value) for value in originals})},
    )
    aliases = {row.normalized_key: row.preferred_term for row in rows}
    return {value: aliases.get(normalize_key(value), value) for value in originals}
