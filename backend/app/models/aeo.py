"""Models for Answer Engine Optimization (AEO).

Covers People-Also-Ask extraction, question clustering / FAQ mapping, combined
JSON-LD schema graphs, internal-link suggestions, and voice-search audits.
"""
from __future__ import annotations

from pydantic import Field

from app.models.common import AppModel

# ---- PAA / autocomplete extraction ----


class QuestionExtractRequest(AppModel):
    """Extract PAA questions, follow-up chains, and autocomplete pathways."""

    seed: str
    depth: int = Field(default=2, ge=1, le=3)          # follow-up chain depth
    per_level: int = Field(default=4, ge=1, le=10)     # questions per expansion level
    include_autocomplete: bool = True
    autocomplete_limit: int = Field(default=10, ge=1, le=25)


class PAAQuestion(AppModel):
    question: str
    parent: str | None = None      # question this one was expanded from (None = root)
    depth: int = 0                 # 0 for seed-level questions


class QuestionExtractionResult(AppModel):
    seed: str
    questions: list[PAAQuestion] = []
    autocomplete: list[str] = []


# ---- Topic clusters & Q&A mapping ----


class PageRef(AppModel):
    url: str
    title: str = ""


class ClusterMapRequest(AppModel):
    questions: list[str]
    pages: list[PageRef] = []      # candidate target pages for FAQ mapping
    similarity_threshold: float = Field(default=0.25, ge=0.0, le=1.0)


class QuestionCluster(AppModel):
    label: str                     # dominant topic terms
    primary_question: str
    questions: list[str] = []


class FaqEntry(AppModel):
    question: str
    answer_template: str
    target_page: str | None = None


class ClusterMapResult(AppModel):
    clusters: list[QuestionCluster] = []
    faq: list[FaqEntry] = []


# ---- Combined JSON-LD schema graph ----


class QAItem(AppModel):
    question: str
    answer: str


class HowToStep(AppModel):
    name: str
    text: str = ""


class HowToInput(AppModel):
    name: str
    steps: list[HowToStep] = []


class BreadcrumbItem(AppModel):
    name: str
    url: str


class SchemaGraphRequest(AppModel):
    """Page content used to assemble a combined ``@graph`` JSON-LD block."""

    url: str
    title: str
    description: str = ""
    breadcrumbs: list[BreadcrumbItem] = []
    faqs: list[QAItem] = []        # -> FAQPage node
    qa: QAItem | None = None       # -> QAPage node
    how_to: HowToInput | None = None


class SchemaGraphResult(AppModel):
    json_ld: dict[str, object]
    script_tag: str
    node_types: list[str] = []
    warnings: list[str] = []


# ---- Dynamic internal linking ----


class PageDoc(AppModel):
    url: str
    title: str = ""
    body: str = ""
    existing_links: list[str] = []  # outbound internal links already on the page


class LinkSuggestRequest(AppModel):
    pages: list[PageDoc]
    similarity_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    max_per_page: int = Field(default=5, ge=1, le=20)


class LinkSuggestion(AppModel):
    source_url: str
    target_url: str
    similarity: float
    anchor_text: str


class LinkSuggestResult(AppModel):
    suggestions: list[LinkSuggestion] = []
    pages_analyzed: int = 0


# ---- Voice search readiness audit ----


class VoiceAuditRequest(AppModel):
    content: str
    question: str | None = None            # spoken query the content should answer
    answer_word_limit: int = Field(default=50, ge=10, le=200)


class VoiceCheck(AppModel):
    code: str
    label: str
    passed: bool
    weight: int = 1
    message: str = ""


class VoiceAuditResult(AppModel):
    score: int = 0
    grade: str = "F"
    flesch: float = 0.0
    avg_sentence_length: float = 0.0
    syllable_density: float = 0.0          # syllables per word
    first_paragraph_words: int = 0
    checks: list[VoiceCheck] = []
    fixes: list[str] = []
