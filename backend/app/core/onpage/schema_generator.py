"""Schema.org JSON-LD generator (Rank Math schema-generator style)."""
from __future__ import annotations

import json

from app.models.onpage import SchemaRequest, SchemaResult, SchemaType

# Recommended fields per schema type; missing (or empty) ones produce a warning.
# Types not listed here (BreadcrumbList, Person, VideoObject) have no mandated
# recommended fields but are still fully supported for generation.
_RECOMMENDED_FIELDS: dict[SchemaType, list[str]] = {
    SchemaType.ARTICLE: ["headline", "author", "datePublished"],
    SchemaType.PRODUCT: ["name", "offers"],
    SchemaType.FAQ: ["mainEntity"],
    SchemaType.LOCAL_BUSINESS: ["name", "address"],
    SchemaType.HOW_TO: ["step"],
    SchemaType.EVENT: ["startDate", "location"],
    SchemaType.RECIPE: ["recipeIngredient"],
    SchemaType.ORGANIZATION: ["name", "url"],
    SchemaType.WEBSITE: ["name", "url"],
}


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, list, dict, tuple, set)):
        return len(value) == 0
    return False


def _missing_recommended_fields(schema_type: SchemaType, fields: dict[str, object]) -> list[str]:
    recommended = _RECOMMENDED_FIELDS.get(schema_type, [])
    return [name for name in recommended if name not in fields or _is_empty(fields[name])]


def generate_schema(req: SchemaRequest) -> SchemaResult:
    """Build a JSON-LD structured-data block for ``req.schema_type``.

    ``req.fields`` are merged in as-is using their keys as schema.org property
    names (e.g. ``headline``, ``author``, ``offers``), alongside the mandatory
    ``@context`` / ``@type`` keys. Warnings flag missing recommended fields for
    the well-known schema types; unrecognized types still generate cleanly with
    no recommended-field warnings.
    """
    json_ld: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": req.schema_type.value,
    }
    json_ld.update(req.fields)

    script_tag = '<script type="application/ld+json">' + json.dumps(json_ld, ensure_ascii=False) + "</script>"

    missing = _missing_recommended_fields(req.schema_type, req.fields)
    warnings = [
        f"Missing recommended field '{name}' for {req.schema_type.value} schema." for name in missing
    ]

    return SchemaResult(
        schema_type=req.schema_type,
        json_ld=json_ld,
        script_tag=script_tag,
        warnings=warnings,
    )
