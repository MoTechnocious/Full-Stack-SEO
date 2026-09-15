"""Tests for the on-page + content-optimization engine (Rank Math rule engine +
Surfer-style scoring). Deterministic: no network, no randomness.
"""
from __future__ import annotations

from app.core.onpage.analyzer import analyze_onpage, get_checks
from app.core.onpage.content_score import score_content
from app.core.onpage.nlp import derive_term_targets
from app.core.onpage.readability import readability_report
from app.core.onpage.schema_generator import generate_schema
from app.models.onpage import (
    CheckCategory,
    ContentEditorRequest,
    OnPageRequest,
    SchemaRequest,
    SchemaType,
    TermStatus,
)

# ---------------------------------------------------------------------------
# Fixtures (module-level constants; deterministic, hand-verified word counts)
# ---------------------------------------------------------------------------

GOOD_HTML = """
<!doctype html>
<html lang="en">
<head>
  <title>Best Running Shoes for Beginners (2026 Guide)</title>
  <meta name="description" content="Find the best running shoes for beginners in 2026. Our guide compares comfort, price and support to help you pick the right pair today." />
</head>
<body>
  <h1>Best Running Shoes for Beginners</h1>
  <p>Running shoes are the single most important piece of gear any new runner will buy this year. The best running shoes support your stride, cushion every step, and lower the risk of injury during long training runs. Beginners often assume any sneaker will work, but running shoes are built with specialized foam, breathable mesh, and structured heel support that everyday trainers lack.</p>

  <h2>How We Chose the Best Running Shoes</h2>
  <p>Our editors tested dozens of pairs over three months of real training runs, from short easy jogs to longer weekend efforts. We scored each shoe on comfort, cushioning, breathability, price, and durability. Every pair on this list held up well after many miles on the road and on the treadmill, and every tester said they would buy the shoe again with their own money.</p>
  <p>We also asked a small panel of beginner runners to wear test each shoe for two weeks. Their feedback shaped the final rankings just as much as our lab measurements did, because comfort out of the box matters most to someone who is new to the sport and still building a habit.</p>

  <h2>Top Picks and Buying Tips for New Runners</h2>
  <p>If you are buying your first pair, start with a true neutral trainer that offers soft cushioning and a roomy toe box. Beginner runners tend to overstride early on, so extra cushioning under the heel can make those first few weeks far more comfortable and help you stay consistent with training.</p>
  <p>Price matters too. You do not need to spend a fortune on your first pair of running shoes; many affordable options perform just as well as premium models for someone running fewer than twenty miles per week. Replace your shoes every three to five hundred miles to keep the cushioning fresh and to avoid injury.</p>
  <p>Finally, always try shoes on later in the day when your feet are slightly swollen, and walk around the store for a few minutes. A good running shoe should feel comfortable immediately; do not count on a long break in period to fix a poor fit. For more help pairing shoes with a training plan, read our beginner runners guide before your next purchase.</p>

  <h2>Shoe Anatomy Explained</h2>
  <p>A modern trainer is built from several key layers working together. The outsole grips the road and resists wear, the midsole absorbs shock with foam or gel, and the upper wraps the foot in breathable mesh to keep it cool and secure. Manufacturers also add a firmer heel counter to control side to side motion, which matters most for runners who log longer distances every week. Understanding these parts helps you compare models more confidently, rather than choosing based on color or brand name alone. Once you know what each layer does, reading a shoe review becomes far easier and far more useful for your own decision.</p>

  <h2>Finding Your Foot Type</h2>
  <p>Every runner's foot strikes the ground a little differently, and that pattern is often called pronation. Some feet roll inward slightly on impact, which is normal, while others roll excessively or barely at all. A specialty running store can watch you walk or jog on a treadmill and recommend a shoe shape that matches your natural motion. Getting this fit right early on can prevent nagging knee and hip pain later in your training. Do not worry if you are unsure of your foot type before your first purchase; most neutral trainers work well for the majority of new runners and can always be adjusted after a few months of steady mileage.</p>

  <h2>Weather and Rotation Tips</h2>
  <p>Weather also shapes which pair you should reach for on a given morning. Lightweight, breathable mesh keeps feet cool during hot summer training, while a water resistant upper helps in rain or light snow. Many beginners keep two pairs in rotation, alternating each run so the cushioning has time to fully recover between sessions. This simple habit can extend the life of both pairs and reduce the repetitive strain that comes from wearing the same midsole every single day. A rotation also gives you a backup ready to go if one pair gets soaked on a rainy commute.</p>

  <h2>Caring for Your Shoes</h2>
  <p>Basic care extends the life of any trainer. Let a wet pair air dry away from direct heat, remove the insole to speed drying, and avoid tossing them in a hot dryer, which can warp the foam and shorten its lifespan. Loosen the laces fully before you take shoes off so the heel counter keeps its shape over time. Store shoes somewhere dry between runs rather than leaving them balled up in a gym bag for days. These small habits cost nothing and can add real mileage to a pair you already love wearing on every run.</p>

  <p>With the right pair of running shoes, a sensible rotation, and a little routine care, your first months of training will feel far more comfortable and far less prone to injury.</p>

  <img src="/img/shoe1.jpg" alt="Best running shoes for beginners on a track" />
  <img src="/img/shoe2.jpg" alt="Close up of running shoe cushioning and sole" />

  <a href="/guides/marathon-training">Marathon training guide</a>
  <a href="https://www.runnersworld.com/gear" rel="nofollow">Runner's World gear reviews</a>
</body>
</html>
"""  # noqa: E501

POOR_HTML = """
<!doctype html>
<html>
<head><title>Home</title></head>
<body>
<p>Welcome to our site. We sell things. Check back soon for updates. Thanks for visiting.</p>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# analyzer.py
# ---------------------------------------------------------------------------


def test_get_checks_structure_and_categories():
    """get_checks returns a well-formed, deterministic rule set covering all 4 categories."""
    req = OnPageRequest(
        target_keyword="seo tool",
        title="A Simple SEO Tool Guide",
        meta_description="x" * 90,
        content="seo tool " * 50,
    )
    checks = get_checks(req)

    assert 18 <= len(checks) <= 24
    codes = [c.code for c in checks]
    assert len(codes) == len(set(codes))  # unique codes
    categories = {c.category for c in checks}
    assert categories == set(CheckCategory)
    for check in checks:
        assert isinstance(check.code, str) and check.code
        assert isinstance(check.label, str) and check.label
        assert isinstance(check.passed, bool)
        assert check.weight >= 1
    # Calling get_checks again is deterministic (no randomness/order drift).
    assert [c.code for c in get_checks(req)] == codes


def test_well_optimized_page_scores_high():
    """A page with the target keyword in title/meta/H1/first paragraph/alt text,
    700+ words, subheadings, links, and media should score high with most checks passed."""
    req = OnPageRequest(
        url="https://example.com/best-running-shoes-guide",
        html=GOOD_HTML,
        target_keyword="running shoes",
        secondary_keywords=["beginner runners", "training plan"],
    )
    result = analyze_onpage(req)

    assert result.score >= 70
    assert result.grade in {"A", "B", "C"}
    assert result.passed_count >= round(result.total_count * 0.8)
    assert result.total_count == 23  # url + html present -> all conditional checks included
    # High-weight basic checks must have passed for a well-optimized page.
    by_code = {c.code: c for c in result.checks}
    assert by_code["kw_in_title"].passed is True
    assert by_code["kw_in_meta_description"].passed is True
    assert by_code["kw_in_h1"].passed is True
    assert by_code["content_length"].passed is True
    assert result.category_scores["basic_seo"] >= 70


def test_poor_page_scores_low():
    """A thin page with no focus keyword anywhere should score low and raise issues."""
    req = OnPageRequest(html=POOR_HTML, target_keyword="running shoes")
    result = analyze_onpage(req)

    assert result.score < 50
    assert result.grade in {"E", "F"}
    assert len(result.issues) > 0
    assert any(issue.code == "kw_in_title" for issue in result.issues)
    by_code = {c.code: c for c in result.checks}
    assert by_code["kw_in_title"].passed is False
    assert by_code["content_length"].passed is False


def test_keyword_density_check_band():
    """The density check passes only within the 0.5%-2.5% band."""

    def _density_check(content: str):
        req = OnPageRequest(
            target_keyword="seo tool", title="x" * 20, meta_description="y" * 80, content=content
        )
        return next(c for c in get_checks(req) if c.code == "kw_density")

    absent = _density_check("This article talks about marketing strategy and planning for teams. " * 10)
    assert absent.passed is False

    base = ("This guide explains helpful ideas for growing an online presence over time. " * 20).split()
    good_content = " ".join(base[:150] + ["seo", "tool"] * 3 + base[150:250])
    good = _density_check(good_content)
    assert good.passed is True

    stuffed = "seo tool " * 40 + ("This guide explains helpful ideas for growing an online presence. " * 5)
    over = _density_check(stuffed)
    assert over.passed is False


# ---------------------------------------------------------------------------
# nlp.py
# ---------------------------------------------------------------------------


def test_derive_term_targets_direct():
    competitor_texts = [
        "Digital marketing strategy requires a clear digital marketing plan for every team.",
        "A good digital marketing plan aligns content across every digital marketing channel.",
    ]
    targets = derive_term_targets(competitor_texts, content="digital marketing is on the roadmap", top_k=10)

    assert len(targets) > 0
    # Deterministic ordering: importance is non-increasing.
    importances = [t.importance for t in targets]
    assert importances == sorted(importances, reverse=True)
    assert all(t.status in (TermStatus.UNDER, TermStatus.OPTIMAL, TermStatus.OVER) for t in targets)
    assert derive_term_targets([], content="anything") == []


# ---------------------------------------------------------------------------
# content_score.py
# ---------------------------------------------------------------------------


def test_score_content_with_competitors_yields_band_and_term_statuses():
    competitor_texts = [
        "Digital marketing strategy requires a clear digital marketing plan, strong content "
        "marketing, and consistent social media marketing efforts. Digital marketing teams "
        "should track digital marketing KPIs weekly.",
        "A good digital marketing plan aligns content marketing, email marketing, and social "
        "media marketing into one digital marketing funnel. Digital marketing success depends "
        "on testing.",
        "Effective digital marketing combines content marketing, search engine optimization, "
        "and social media marketing. Digital marketing budgets should prioritize channels that "
        "convert most.",
    ]
    req = ContentEditorRequest(
        target_keyword="digital marketing",
        content="Digital marketing is important. This short article briefly mentions digital marketing once more.",
        secondary_keywords=["content marketing"],
    )
    result = score_content(req, competitor_texts=competitor_texts)

    assert result.word_count_target_min > 0
    assert result.word_count_target_max > result.word_count_target_min
    statuses = {t.status for t in result.term_targets}
    assert TermStatus.UNDER in statuses
    assert TermStatus.OPTIMAL in statuses
    assert len(result.missing_terms) > 0  # short content leaves many competitor terms uncovered
    assert 0 <= result.seo_score <= 100
    assert 0 <= result.content_score <= 100
    assert result.ai_search_score is not None and 0 <= result.ai_search_score <= 100
    assert len(result.suggestions) > 0


def test_score_content_default_band_and_synthesized_terms_without_competitors():
    req = ContentEditorRequest(
        target_keyword="content marketing",
        content="Content marketing is a long-term strategy. " * 5,
        secondary_keywords=["blogging tips"],
    )
    result = score_content(req)

    # No competitor data supplied -> default word-count band applies.
    assert (result.word_count_target_min, result.word_count_target_max) == (800, 1500)
    # Terms are synthesized from target_keyword + secondary_keywords.
    terms = {t.term for t in result.term_targets}
    assert any("content" in t or "marketing" in t or "blogging" in t for t in terms)
    assert 0 <= result.content_score <= 100


# ---------------------------------------------------------------------------
# schema_generator.py
# ---------------------------------------------------------------------------


def test_generate_schema_article_complete_has_no_warnings():
    req = SchemaRequest(
        schema_type=SchemaType.ARTICLE,
        fields={
            "headline": "Best Running Shoes for Beginners",
            "author": {"@type": "Person", "name": "Jane Doe"},
            "datePublished": "2026-01-01",
        },
    )
    result = generate_schema(req)

    assert result.warnings == []
    assert result.json_ld["@context"] == "https://schema.org"
    assert result.json_ld["@type"] == "Article"
    assert "ld+json" in result.script_tag
    assert result.script_tag.startswith("<script")


def test_generate_schema_faq_missing_main_entity_warns():
    req = SchemaRequest(schema_type=SchemaType.FAQ, fields={"name": "FAQ"})
    result = generate_schema(req)

    assert len(result.warnings) == 1
    assert "mainEntity" in result.warnings[0]
    assert "ld+json" in result.script_tag


def test_generate_schema_supports_all_schema_types():
    for schema_type in SchemaType:
        result = generate_schema(SchemaRequest(schema_type=schema_type, fields={"name": "Example"}))
        assert result.schema_type == schema_type
        assert result.json_ld["@type"] == schema_type.value
        assert "ld+json" in result.script_tag


# ---------------------------------------------------------------------------
# readability.py
# ---------------------------------------------------------------------------


def test_readability_report_flesch_in_range():
    report = readability_report("This is a simple short sentence. It has two easy parts to read.")

    assert isinstance(report["flesch"], float)
    assert 0.0 <= report["flesch"] <= 100.0
    assert report["word_count"] > 0
    assert report["sentence_count"] >= 1
    assert report["grade_label"] in {
        "very_easy", "easy", "fairly_easy", "standard", "fairly_difficult", "difficult", "very_difficult",
    }
