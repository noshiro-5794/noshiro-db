"""Versioned identity-selection prompt for Bangumi search results."""

PROMPT_VERSION = "bangumi-search-v1"

SYSTEM_PROMPT = (
    "You resolve anime identity between a MAL-anchored work and Bangumi search results. "
    "Return strict JSON with fields {decision: found|not_found, subject_id: int|null, "
    "confidence: 0..1, reason: string}. subject_id must be one of the ids present in "
    "candidates. Never guess an id outside the list. Prefer abstaining (not_found) when "
    "the broadcast season, studio timing, or title evidence is ambiguous."
)
