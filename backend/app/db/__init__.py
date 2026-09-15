"""Database layer: SQLModel engine/session + all persistence tables.

Importing this package registers every table on ``SQLModel.metadata`` so
``init_db()`` can create them.
"""
from app.db import models_billing, models_seo, models_tenancy  # noqa: F401
from app.db.session import get_session, init_db

__all__ = ["get_session", "init_db", "models_tenancy", "models_billing", "models_seo"]
