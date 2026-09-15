"""Models for Personal Entity Optimization (PEO).

Covers the Knowledge Graph explorer/sensor, entity bio building, cross-source
corroboration auditing, and Person/Organization entity schema generation.
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field

from app.models.common import AppModel

# ---- Knowledge Graph explorer ----


class EntitySearchRequest(AppModel):
    """Query the (mock) Google Knowledge Graph Search API."""

    query: str
    types: list[str] = []          # optional schema.org type filter, e.g. ["Person"]
    limit: int = Field(default=10, ge=1, le=50)


class KGEntity(AppModel):
    """A single Knowledge Graph entity candidate."""

    kg_mid: str                    # machine ID, e.g. "/g/1a2b3c4d5e"
    name: str
    types: list[str] = []
    description: str = ""
    result_score: float = 0.0      # KG API result score (unbounded, higher = stronger)
    url: str | None = None


class EntitySearchResult(AppModel):
    query: str
    entities: list[KGEntity] = []


class EntityTrackRequest(AppModel):
    """Register a KGMID for org-scoped tracking by the KG sensor."""

    kg_mid: str
    name: str
    types: list[str] = []
    description: str = ""


class TrackedEntity(AppModel):
    kg_mid: str
    name: str
    types: list[str] = []
    description: str = ""
    latest_score: float = 0.0


# ---- Knowledge Graph sensor ----


class SensorObservation(AppModel):
    """One confidence-score reading in an entity's time series."""

    observed_at: str               # ISO date (YYYY-MM-DD)
    score: float


class TrendClass(str, Enum):
    RISING = "rising"
    STABLE = "stable"
    VOLATILE = "volatile"
    DECLINING = "declining"


class SensorReport(AppModel):
    """Volatility + trend analysis over an entity's confidence-score series."""

    kg_mid: str
    name: str = ""
    observations: list[SensorObservation] = []
    latest_score: float = 0.0
    mean_score: float = 0.0
    net_change: float = 0.0        # last score minus first score
    volatility: float = 0.0        # stddev of consecutive deltas
    trend: TrendClass = TrendClass.STABLE


# ---- Entity description (bio) builder ----


class BioLength(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class BioRequest(AppModel):
    """Structured facts used to assemble an NLP-optimized entity bio."""

    name: str
    roles: list[str] = []          # e.g. ["CEO", "angel investor"]
    organizations: list[str] = []  # first item is treated as the primary affiliation
    works: list[str] = []          # books, products, notable projects
    credentials: list[str] = []    # degrees, awards, certifications
    location: str | None = None
    websites: list[str] = []


class BioVariant(AppModel):
    length: BioLength
    text: str
    word_count: int = 0
    triple_count: int = 0          # subject-predicate-object facts asserted
    triple_density: float = 0.0    # triples per sentence


class BioResult(AppModel):
    name: str
    variants: list[BioVariant] = []
    warnings: list[str] = []


# ---- Corroboration mapping ----


class SourceType(str, Enum):
    WIKIPEDIA = "wikipedia"
    WIKIDATA = "wikidata"
    CRUNCHBASE = "crunchbase"
    LINKEDIN = "linkedin"
    OWN_SITE = "own_site"


class SourceProfile(AppModel):
    """Key facts as asserted by one external (or owned) profile."""

    source: SourceType
    url: str | None = None
    facts: dict[str, str] = {}


class CorroborationRequest(AppModel):
    """Canonical narrative + source profiles to diff for consistency."""

    entity_name: str
    canonical_facts: dict[str, str]
    profiles: list[SourceProfile] = []
    fetch_sources: list[SourceType] = []   # resolved via the injected ProfileFetcher


class FactStatus(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    MISSING = "missing"


class FactComparison(AppModel):
    source: SourceType
    fact: str
    canonical_value: str
    found_value: str | None = None
    status: FactStatus


class CorroborationReport(AppModel):
    entity_name: str
    consistency_score: int = 0     # 0-100 share of corroborated facts
    sources_checked: int = 0
    comparisons: list[FactComparison] = []
    match_count: int = 0
    mismatch_count: int = 0
    missing_count: int = 0
    fixes: list[str] = []


# ---- Entity schema generator ----


class EntityType(str, Enum):
    PERSON = "Person"
    ORGANIZATION = "Organization"


class EntitySchemaRequest(AppModel):
    """Inputs for a relationally-linked Person/Organization JSON-LD block."""

    entity_type: EntityType
    name: str
    url: str | None = None
    description: str | None = None
    same_as: list[str] = []        # corroborating profile URLs -> sameAs
    image: str | None = None
    # Person-oriented relations
    job_title: str | None = None
    works_for: str | None = None
    founder_of: list[str] = []     # organizations founded (emitted via @reverse founder)
    author_of: list[str] = []      # creative works authored (emitted via @reverse author)
    alumni_of: list[str] = []
    # Organization-oriented relations
    logo: str | None = None
    founding_date: str | None = None
    founders: list[str] = []


class EntitySchemaResult(AppModel):
    entity_type: EntityType
    json_ld: dict[str, object]
    script_tag: str
    warnings: list[str] = []
