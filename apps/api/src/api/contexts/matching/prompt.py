"""Versioned work identity adjudication prompt."""

PROMPT_VERSION = "entity-match-v2"
SYSTEM_PROMPT = (
    "Decide whether two knowledge-base works from different providers are the same "
    "real work. The payload gives you left_work and right_work - each with the names "
    "the provider stores, the release date, the episode count, the platform and the "
    "external links the catalogue already holds - and comparison, which summarises "
    "how far the two sides agree. A hard conflict means the two cannot be the same "
    "work. Bind only when the titles agree AND at least one independent attribute "
    "corroborates them (release date within a year, matching episode count, or "
    "matching platform); a translated or romanised title alone is not enough, because "
    "unrelated works share translations. Return strict JSON with decision (bind, "
    "group, reject, or abstain), confidence from 0 to 1, and a concise reason. Use "
    "'group' when the works belong to the same season or series at different "
    "granularity (e.g. one whole season versus its split cours) and must not be "
    "merged. Abstain whenever the evidence leaves real doubt."
)
