"""Corroboration mapping: diff an entity's canonical facts across source profiles.

Knowledge panels and answer engines reward *consistency*: the same key facts
asserted identically on Wikipedia, Wikidata, Crunchbase, LinkedIn, and the
entity's own site. This engine compares each source profile against the
canonical narrative, flags mismatches and gaps, and produces a consistency
score plus an actionable fix list.
"""
from __future__ import annotations

import re

from app.models.peo import (
    CorroborationReport,
    FactComparison,
    FactStatus,
    SourceProfile,
)

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def _normalize(value: str) -> str:
    """Casefold and strip punctuation/whitespace so cosmetic diffs don't flag."""
    return _NORMALIZE_RE.sub(" ", (value or "").lower()).strip()


def _compare_profile(
    canonical_facts: dict[str, str], profile: SourceProfile
) -> list[FactComparison]:
    comparisons: list[FactComparison] = []
    for fact, canonical_value in canonical_facts.items():
        found = profile.facts.get(fact)
        if found is None or not found.strip():
            status, found_value = FactStatus.MISSING, None
        elif _normalize(found) == _normalize(canonical_value):
            status, found_value = FactStatus.MATCH, found
        else:
            status, found_value = FactStatus.MISMATCH, found
        comparisons.append(
            FactComparison(
                source=profile.source,
                fact=fact,
                canonical_value=canonical_value,
                found_value=found_value,
                status=status,
            )
        )
    return comparisons


def _fix_for(comparison: FactComparison) -> str:
    if comparison.status == FactStatus.MISMATCH:
        return (
            f"Update '{comparison.fact}' on {comparison.source.value} from "
            f"'{comparison.found_value}' to '{comparison.canonical_value}'."
        )
    return (
        f"Add '{comparison.fact}' = '{comparison.canonical_value}' to the "
        f"{comparison.source.value} profile."
    )


def audit_corroboration(
    entity_name: str,
    canonical_facts: dict[str, str],
    profiles: list[SourceProfile],
) -> CorroborationReport:
    """Diff ``canonical_facts`` against every source profile.

    The consistency score is the percentage of (source, fact) comparisons that
    matched; missing facts count against the score because uncorroborated facts
    weaken entity confidence just like contradicted ones. An empty comparison
    set (no profiles or no canonical facts) scores 100 — nothing contradicts
    the canonical narrative.
    """
    comparisons: list[FactComparison] = []
    for profile in profiles:
        comparisons.extend(_compare_profile(canonical_facts, profile))

    matches = sum(1 for c in comparisons if c.status == FactStatus.MATCH)
    mismatches = sum(1 for c in comparisons if c.status == FactStatus.MISMATCH)
    missing = sum(1 for c in comparisons if c.status == FactStatus.MISSING)
    score = round(100 * matches / len(comparisons)) if comparisons else 100
    fixes = [_fix_for(c) for c in comparisons if c.status != FactStatus.MATCH]

    return CorroborationReport(
        entity_name=entity_name,
        consistency_score=score,
        sources_checked=len(profiles),
        comparisons=comparisons,
        match_count=matches,
        mismatch_count=mismatches,
        missing_count=missing,
        fixes=fixes,
    )
