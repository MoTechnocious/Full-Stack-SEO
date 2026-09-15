"""Automated JSON-LD schema graphs: one ``@graph`` block per page.

Combines WebPage, BreadcrumbList, FAQPage, QAPage, and HowTo nodes into a
single ``@graph`` with stable ``@id`` anchors. Individual node bodies are
generated through the on-page schema generator (reused read-only) so the
recommended-field warnings stay consistent with the /onpage/schema endpoint.
"""
from __future__ import annotations

import json

from app.core.onpage.schema_generator import generate_schema
from app.models.aeo import SchemaGraphRequest, SchemaGraphResult
from app.models.onpage import SchemaRequest, SchemaType


def _node_from(schema_type: SchemaType, fields: dict[str, object], node_id: str,
               warnings: list[str]) -> dict[str, object]:
    """Generate a node via the shared generator, strip ``@context``, anchor ``@id``."""
    result = generate_schema(SchemaRequest(schema_type=schema_type, fields=fields))
    warnings.extend(result.warnings)
    node = {k: v for k, v in result.json_ld.items() if k != "@context"}
    node["@id"] = node_id
    return node


def build_schema_graph(req: SchemaGraphRequest) -> SchemaGraphResult:
    """Assemble a combined JSON-LD ``@graph`` for one page.

    A WebPage node is always present; BreadcrumbList / FAQPage / QAPage / HowTo
    nodes are added when the corresponding content exists. Validation never
    blocks generation — problems surface as warnings.
    """
    warnings: list[str] = []
    nodes: list[dict[str, object]] = []
    base = req.url.rstrip("/") or req.url

    web_page: dict[str, object] = {
        "@type": "WebPage",
        "@id": f"{base}#webpage",
        "url": req.url,
        "name": req.title,
    }
    if req.description:
        web_page["description"] = req.description
    nodes.append(web_page)

    if req.breadcrumbs:
        item_list = [
            {"@type": "ListItem", "position": i + 1, "name": crumb.name, "item": crumb.url}
            for i, crumb in enumerate(req.breadcrumbs)
        ]
        nodes.append(
            _node_from(SchemaType.BREADCRUMB, {"itemListElement": item_list},
                       f"{base}#breadcrumb", warnings)
        )
        web_page["breadcrumb"] = {"@id": f"{base}#breadcrumb"}

    if req.faqs:
        main_entity = [
            {
                "@type": "Question",
                "name": item.question,
                "acceptedAnswer": {"@type": "Answer", "text": item.answer},
            }
            for item in req.faqs
        ]
        nodes.append(
            _node_from(SchemaType.FAQ, {"mainEntity": main_entity}, f"{base}#faq", warnings)
        )

    if req.qa is not None:
        nodes.append(
            {
                "@type": "QAPage",
                "@id": f"{base}#qapage",
                "mainEntity": {
                    "@type": "Question",
                    "name": req.qa.question,
                    "answerCount": 1,
                    "acceptedAnswer": {"@type": "Answer", "text": req.qa.answer},
                },
            }
        )

    if req.how_to is not None:
        steps = [
            {"@type": "HowToStep", "name": step.name, "text": step.text or step.name}
            for step in req.how_to.steps
        ]
        nodes.append(
            _node_from(
                SchemaType.HOW_TO,
                {"name": req.how_to.name, "step": steps},
                f"{base}#howto",
                warnings,
            )
        )

    if len(nodes) == 1:
        warnings.append(
            "No answer-engine nodes (FAQPage/QAPage/HowTo) were generated; "
            "provide faqs, qa, or how_to content to qualify for rich results."
        )

    json_ld: dict[str, object] = {"@context": "https://schema.org", "@graph": nodes}
    script_tag = (
        '<script type="application/ld+json">'
        + json.dumps(json_ld, ensure_ascii=False)
        + "</script>"
    )
    node_types = [str(node["@type"]) for node in nodes]

    return SchemaGraphResult(
        json_ld=json_ld, script_tag=script_tag, node_types=node_types, warnings=warnings
    )
