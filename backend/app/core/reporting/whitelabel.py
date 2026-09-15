"""White-label agency branding overlay.

Deterministic, side-effect-free merge of partial branding overrides onto
:class:`~app.models.reporting.WhiteLabelBranding` defaults. Designed to never raise
on partial, missing, or malformed input — callers can pass whatever they have (a
dict from a settings form, a stored model, or nothing at all).
"""
from __future__ import annotations

from app.models.reporting import WhiteLabelBranding


def apply_branding(overrides: dict[str, object] | WhiteLabelBranding | None) -> WhiteLabelBranding:
    """Merge ``overrides`` onto the default branding.

    * ``None`` -> pure defaults.
    * A :class:`WhiteLabelBranding` instance -> returned as-is (already fully populated).
    * A ``dict`` -> shallow-merged onto the defaults; unknown keys are ignored, ``None``
      values are treated as "not provided" (default kept), and any value that fails
      validation for its field is dropped rather than raising.
    """
    if overrides is None:
        return WhiteLabelBranding()
    if isinstance(overrides, WhiteLabelBranding):
        return overrides
    if not isinstance(overrides, dict):
        return WhiteLabelBranding()

    base: dict[str, object] = WhiteLabelBranding().model_dump()
    candidate = dict(base)
    for key, value in overrides.items():
        if key in base and value is not None:
            candidate[key] = value

    try:
        return WhiteLabelBranding(**candidate)
    except Exception:
        pass

    # A single malformed field shouldn't sink the whole merge: re-apply overrides one
    # at a time, keeping only the ones that individually validate.
    safe = dict(base)
    for key, value in overrides.items():
        if key not in base or value is None:
            continue
        trial = dict(safe)
        trial[key] = value
        try:
            WhiteLabelBranding(**trial)
        except Exception:
            continue
        safe[key] = value
    return WhiteLabelBranding(**safe)
