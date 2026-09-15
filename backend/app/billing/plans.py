"""Plan catalog + entitlements.

Plans are defined in code (source of truth); the DB only stores which plan each
org is on. Limits use ``-1`` for unlimited. Metric keys match usage metric names.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Feature flags
F_WHITE_LABEL = "white_label"
F_API_ACCESS = "api_access"
F_MCP_ACCESS = "mcp_access"
F_CONTENT_AI = "content_ai"
F_COMPETITOR = "competitor_analysis"
F_SCHEDULED = "scheduled_crawls"
F_PRIORITY = "priority_support"
F_AI_TRACKER = "ai_tracker"  # v2 answer-engine tracking (entry tier: ChatGPT-only, weekly)
F_AI_TRACKER_ALL_ENGINES = "ai_tracker_all_engines"  # all five engines + daily refresh

# Limit metric keys
L_SITES = "sites"
L_TRACKED_KEYWORDS = "tracked_keywords"
L_CRAWLS = "crawls_per_month"
L_PAGES_PER_CRAWL = "pages_per_crawl"
L_CONTENT_SCORES = "content_scores_per_month"
L_KEYWORD_LOOKUPS = "keyword_lookups_per_month"
L_REPORTS = "reports_per_month"
L_SEATS = "seats"
L_AI_TRACKER_CONFIGS = "ai_tracker_configs"
L_AI_TRACKER_PROMPTS = "ai_tracker_prompts_per_config"


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    price_monthly: float
    price_annual: float
    limits: dict[str, int]
    features: frozenset[str] = field(default_factory=frozenset)
    description: str = ""
    is_custom: bool = False

    def limit(self, metric: str) -> int:
        return self.limits.get(metric, 0)

    def has_feature(self, feature: str) -> bool:
        return feature in self.features


_ALL_FEATURES = frozenset(
    {F_WHITE_LABEL, F_API_ACCESS, F_MCP_ACCESS, F_CONTENT_AI, F_COMPETITOR, F_SCHEDULED, F_PRIORITY,
     F_AI_TRACKER, F_AI_TRACKER_ALL_ENGINES}
)

PLANS: dict[str, Plan] = {
    "free": Plan(
        code="free",
        name="Free",
        price_monthly=0.0,
        price_annual=0.0,
        description="Try the platform on a single site.",
        limits={
            L_SITES: 1, L_TRACKED_KEYWORDS: 25, L_CRAWLS: 5, L_PAGES_PER_CRAWL: 100,
            L_CONTENT_SCORES: 10, L_KEYWORD_LOOKUPS: 50, L_REPORTS: 2, L_SEATS: 1,
            L_AI_TRACKER_CONFIGS: 0, L_AI_TRACKER_PROMPTS: 0,
        },
        features=frozenset(),
    ),
    "starter": Plan(
        code="starter",
        name="Starter",
        price_monthly=29.0,
        price_annual=290.0,
        description="For freelancers and small businesses.",
        limits={
            L_SITES: 3, L_TRACKED_KEYWORDS: 200, L_CRAWLS: 30, L_PAGES_PER_CRAWL: 1_000,
            L_CONTENT_SCORES: 100, L_KEYWORD_LOOKUPS: 500, L_REPORTS: 20, L_SEATS: 3,
            L_AI_TRACKER_CONFIGS: 0, L_AI_TRACKER_PROMPTS: 0,
        },
        features=frozenset({F_API_ACCESS, F_CONTENT_AI}),
    ),
    "pro": Plan(
        code="pro",
        name="Pro",
        price_monthly=79.0,
        price_annual=790.0,
        description="For in-house SEO teams.",
        limits={
            L_SITES: 10, L_TRACKED_KEYWORDS: 1_000, L_CRAWLS: 150, L_PAGES_PER_CRAWL: 10_000,
            L_CONTENT_SCORES: 500, L_KEYWORD_LOOKUPS: 2_500, L_REPORTS: 100, L_SEATS: 10,
            L_AI_TRACKER_CONFIGS: 5, L_AI_TRACKER_PROMPTS: 25,
        },
        features=frozenset(
            {F_API_ACCESS, F_MCP_ACCESS, F_CONTENT_AI, F_COMPETITOR, F_SCHEDULED, F_AI_TRACKER}
        ),
    ),
    "agency": Plan(
        code="agency",
        name="Agency",
        price_monthly=199.0,
        price_annual=1_990.0,
        description="For agencies managing many client sites, with white-label reporting.",
        limits={
            L_SITES: 50, L_TRACKED_KEYWORDS: 5_000, L_CRAWLS: 1_000, L_PAGES_PER_CRAWL: 50_000,
            L_CONTENT_SCORES: 2_500, L_KEYWORD_LOOKUPS: 10_000, L_REPORTS: 1_000, L_SEATS: 25,
            L_AI_TRACKER_CONFIGS: 25, L_AI_TRACKER_PROMPTS: 100,
        },
        features=_ALL_FEATURES,
    ),
    "enterprise": Plan(
        code="enterprise",
        name="Enterprise",
        price_monthly=0.0,
        price_annual=0.0,
        description="Custom limits, SSO, and priority support.",
        is_custom=True,
        limits={
            L_SITES: -1, L_TRACKED_KEYWORDS: -1, L_CRAWLS: -1, L_PAGES_PER_CRAWL: -1,
            L_CONTENT_SCORES: -1, L_KEYWORD_LOOKUPS: -1, L_REPORTS: -1, L_SEATS: -1,
            L_AI_TRACKER_CONFIGS: -1, L_AI_TRACKER_PROMPTS: -1,
        },
        features=_ALL_FEATURES,
    ),
}


def get_plan(code: str | None) -> Plan:
    return PLANS.get((code or "free").lower(), PLANS["free"])


def list_plans() -> list[Plan]:
    return list(PLANS.values())
