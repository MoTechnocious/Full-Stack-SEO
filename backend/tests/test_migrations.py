"""Alembic migration tests.

Verifies that ``alembic upgrade head`` on a fresh SQLite database produces a
schema equivalent to ``SQLModel.metadata.create_all()`` (table names, columns,
types, nullability), and that ``downgrade base`` removes everything again.

Skips gracefully when alembic is not installed (it is a production/deploy
dependency; the app itself never imports it).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

alembic = pytest.importorskip("alembic")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)  # informational
    cfg.attributes["configure_logger"] = False

    class _Opts:
        # env.py resolves -x db_url first, before SEO_DATABASE_URL / defaults.
        x = [f"db_url={db_url}"]

    cfg.cmd_opts = _Opts()
    return cfg


def _schema_snapshot(engine, skip: tuple[str, ...] = ("alembic_version",)) -> dict:
    insp = inspect(engine)
    snapshot: dict[str, list] = {}
    for table in insp.get_table_names():
        if table in skip:
            continue
        snapshot[table] = sorted(
            (col["name"], str(col["type"]).upper(), bool(col["nullable"]))
            for col in insp.get_columns(table)
        )
    return snapshot


def test_upgrade_head_matches_metadata(tmp_path: Path) -> None:
    """upgrade head == SQLModel.metadata.create_all (tables + columns)."""
    import app.db  # noqa: F401  (register all models on SQLModel.metadata)

    migrated_url = f"sqlite:///{tmp_path / 'migrated.db'}"
    command.upgrade(_alembic_config(migrated_url), "head")

    metadata_url = f"sqlite:///{tmp_path / 'metadata.db'}"
    meta_engine = create_engine(metadata_url)
    SQLModel.metadata.create_all(meta_engine)

    migrated = _schema_snapshot(create_engine(migrated_url))
    expected = _schema_snapshot(meta_engine)

    assert set(migrated) == set(expected), (
        f"table mismatch: only-in-migration={set(migrated) - set(expected)}, "
        f"only-in-metadata={set(expected) - set(migrated)}"
    )
    for table in expected:
        assert migrated[table] == expected[table], f"column mismatch in {table!r}"
    assert len(expected) > 0


def test_downgrade_base_removes_all_tables(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'updown.db'}"
    cfg = _alembic_config(db_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    remaining = _schema_snapshot(create_engine(db_url))
    assert remaining == {}, f"tables left after downgrade: {sorted(remaining)}"
