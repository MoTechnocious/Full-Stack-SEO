"""Entity schema generator: Person/Organization JSON-LD with strict relational links.

Builds on the generic on-page schema generator (reused read-only for the
``@context``/``@type`` envelope, script tag, and recommended-field warnings)
and layers on properly-typed relational nodes: ``worksFor``, ``alumniOf``,
``founder``, ``sameAs``, and JSON-LD ``@reverse`` links for "founder of" /
"author of" (schema.org models those relations from the other side).
"""
from __future__ import annotations

from app.core.onpage.schema_generator import generate_schema
from app.models.onpage import SchemaRequest, SchemaType
from app.models.peo import EntitySchemaRequest, EntitySchemaResult, EntityType


def _org_node(name: str) -> dict[str, object]:
    return {"@type": "Organization", "name": name}


def _person_fields(req: EntitySchemaRequest) -> dict[str, object]:
    fields: dict[str, object] = {}
    if req.job_title:
        fields["jobTitle"] = req.job_title
    if req.works_for:
        fields["worksFor"] = _org_node(req.works_for)
    if req.alumni_of:
        fields["alumniOf"] = [
            {"@type": "EducationalOrganization", "name": name} for name in req.alumni_of
        ]
    reverse: dict[str, object] = {}
    if req.founder_of:
        reverse["founder"] = [_org_node(name) for name in req.founder_of]
    if req.author_of:
        reverse["author"] = [{"@type": "CreativeWork", "name": name} for name in req.author_of]
    if reverse:
        fields["@reverse"] = reverse
    return fields


def _organization_fields(req: EntitySchemaRequest) -> dict[str, object]:
    fields: dict[str, object] = {}
    if req.logo:
        fields["logo"] = req.logo
    if req.founding_date:
        fields["foundingDate"] = req.founding_date
    if req.founders:
        fields["founder"] = [{"@type": "Person", "name": name} for name in req.founders]
    return fields


def _extra_warnings(req: EntitySchemaRequest) -> list[str]:
    warnings: list[str] = []
    if not req.name.strip():
        warnings.append("Required field 'name' is empty.")
    if req.entity_type == EntityType.PERSON and not req.url:
        warnings.append("Missing recommended field 'url' for Person schema.")
    if not req.same_as:
        warnings.append(
            "Missing 'sameAs' links; add corroborating profile URLs "
            "(Wikipedia, Wikidata, LinkedIn, ...) to strengthen entity disambiguation."
        )
    if req.entity_type == EntityType.PERSON and not (req.job_title or req.works_for):
        warnings.append("Person schema has neither 'jobTitle' nor 'worksFor'; add at least one.")
    if req.entity_type == EntityType.ORGANIZATION and not req.logo:
        warnings.append("Missing recommended field 'logo' for Organization schema.")
    return warnings


def generate_entity_schema(req: EntitySchemaRequest) -> EntitySchemaResult:
    """Build a relationally-linked Person/Organization JSON-LD block.

    Required/recommended-field validation never blocks generation — the block
    is always emitted and problems surface as warnings, matching the behaviour
    of the on-page schema generator.
    """
    fields: dict[str, object] = {"name": req.name}
    if req.url:
        fields["url"] = req.url
    if req.description:
        fields["description"] = req.description
    if req.image:
        fields["image"] = req.image
    if req.same_as:
        fields["sameAs"] = list(req.same_as)
    if req.entity_type == EntityType.PERSON:
        fields.update(_person_fields(req))
        schema_type = SchemaType.PERSON
    else:
        fields.update(_organization_fields(req))
        schema_type = SchemaType.ORGANIZATION

    base = generate_schema(SchemaRequest(schema_type=schema_type, fields=fields))

    warnings = list(base.warnings)
    for warning in _extra_warnings(req):
        if warning not in warnings:
            warnings.append(warning)

    return EntitySchemaResult(
        entity_type=req.entity_type,
        json_ld=base.json_ld,
        script_tag=base.script_tag,
        warnings=warnings,
    )
