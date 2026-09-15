"""Entity description builder: authoritative, NLP-optimized bios.

Every generated sentence is *subject-first* (it opens with the entity name),
because answer engines and knowledge-graph extractors resolve
subject-predicate-object triples most reliably when the subject is explicit
and leads the sentence. Triple density (asserted facts per sentence) is scored
per variant so callers can verify the bio stays information-dense.
"""
from __future__ import annotations

from app.models.peo import BioLength, BioRequest, BioResult, BioVariant
from app.utils.text import sentence_count, word_count

_MIN_FACTS_FOR_AUTHORITY = 3


def _join(items: list[str]) -> str:
    """Oxford-comma-free natural join: 'a', 'a and b', 'a, b and c'."""
    items = [i.strip() for i in items if i.strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _identity_sentence(req: BioRequest) -> tuple[str, int]:
    """Lead sentence: name + role(s) + primary organization + location."""
    triples = 0
    parts = [req.name, "is"]
    if req.roles:
        roles = _join(req.roles[:2])
        article = "an" if roles[:1].lower() in "aeiou" else "a"
        parts.append(f"{article} {roles}")
        triples += min(2, len(req.roles))
    else:
        parts.append("a professional")
    if req.organizations:
        parts.append(f"at {req.organizations[0]}")
        triples += 1
    if req.location:
        parts.append(f"based in {req.location}")
        triples += 1
    return " ".join(parts) + ".", triples


def _fact_sentences(req: BioRequest) -> list[tuple[str, int]]:
    """Supporting subject-first sentences, one predicate family per sentence."""
    sentences: list[tuple[str, int]] = []
    extra_orgs = [o for o in req.organizations[1:] if o.strip()]
    if extra_orgs:
        sentences.append((f"{req.name} also works with {_join(extra_orgs)}.", len(extra_orgs)))
    if req.works:
        sentences.append((f"{req.name} is the creator of {_join(req.works)}.", len(req.works)))
    if req.credentials:
        sentences.append((f"{req.name} holds {_join(req.credentials)}.", len(req.credentials)))
    if req.websites:
        sentences.append(
            (f"{req.name}'s work is documented at {_join(req.websites)}.", len(req.websites))
        )
    return sentences


def _variant(length: BioLength, sentences: list[tuple[str, int]]) -> BioVariant:
    text = " ".join(s for s, _ in sentences)
    triple_count = sum(t for _, t in sentences)
    sc = sentence_count(text)
    return BioVariant(
        length=length,
        text=text,
        word_count=word_count(text),
        triple_count=triple_count,
        triple_density=round(triple_count / sc, 2) if sc else 0.0,
    )


def build_bio(req: BioRequest) -> BioResult:
    """Assemble short/medium/long bio variants from structured entity facts.

    * ``short`` — the identity sentence only (search snippets, social bios).
    * ``medium`` — identity plus up to two supporting fact sentences.
    * ``long`` — every asserted fact (about pages, press kits).
    """
    identity = _identity_sentence(req)
    supporting = _fact_sentences(req)

    variants = [
        _variant(BioLength.SHORT, [identity]),
        _variant(BioLength.MEDIUM, [identity] + supporting[:2]),
        _variant(BioLength.LONG, [identity] + supporting),
    ]

    total_facts = (
        len(req.roles) + len(req.organizations) + len(req.works)
        + len(req.credentials) + len(req.websites) + (1 if req.location else 0)
    )
    warnings: list[str] = []
    if not req.roles:
        warnings.append("No roles provided; the identity sentence falls back to a generic label.")
    if total_facts < _MIN_FACTS_FOR_AUTHORITY:
        warnings.append(
            "Fewer than 3 structured facts provided; add roles, organizations, works or "
            "credentials to raise triple density."
        )
    if not req.websites:
        warnings.append("No websites provided; add owned URLs to support sameAs corroboration.")

    return BioResult(name=req.name, variants=variants, warnings=warnings)
