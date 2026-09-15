"""Service layer: persistence abstraction (in-memory default, DB-ready interface)."""
from app.services.store import InMemoryStore, get_store

__all__ = ["InMemoryStore", "get_store"]
