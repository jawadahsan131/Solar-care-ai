import sys
from pathlib import Path

from fastapi import HTTPException
import pytest

from app.services import appliances
from app.services.appliances import configured_catalog_path
from app.services.catalog import load_catalog

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts import seed_catalog as seed_module
from scripts.seed_catalog import _database_row


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, fields):
        return self

    def order(self, field):
        return self

    def execute(self):
        return type("Response", (), {"data": self.rows})()


class _FakeClient:
    def __init__(self, rows):
        self.query = _FakeQuery(rows)

    def table(self, name):
        assert name == "appliance_catalog"
        return self.query


def test_catalog_is_read_from_supabase_and_normalized(monkeypatch) -> None:
    source_rows = load_catalog(configured_catalog_path())
    monkeypatch.setattr(
        appliances,
        "get_supabase",
        lambda: _FakeClient([source_rows[0]]),
    )
    appliances.get_catalog.cache_clear()
    try:
        rows = appliances.get_catalog()
    finally:
        appliances.get_catalog.cache_clear()

    assert len(rows) == 1
    assert rows[0]["type"] == "ac"
    assert rows[0]["rated_watts"] == 900.0
    assert rows[0]["inverter"] is False


def test_empty_supabase_catalog_has_actionable_error(monkeypatch) -> None:
    monkeypatch.setattr(
        appliances,
        "get_supabase",
        lambda: _FakeClient([]),
    )
    appliances.get_catalog.cache_clear()
    try:
        try:
            appliances.get_catalog()
        except HTTPException as error:
            assert error.status_code == 503
            assert "seed_catalog.py" in error.detail
        else:
            raise AssertionError("Expected an empty catalog to return a setup error")
    finally:
        appliances.get_catalog.cache_clear()


def test_seed_row_id_is_stable_and_compatible_with_table() -> None:
    source = load_catalog(configured_catalog_path())[0]
    first = _database_row(source)
    second = _database_row(source)

    assert first["id"] == second["id"]
    assert first["rated_watts"] == source["rated_watts"]
    assert first["verified"] is False


def test_seed_upserts_catalog_rows_without_deleting_existing_data(monkeypatch) -> None:
    calls = []

    class SeedQuery:
        def upsert(self, rows, on_conflict):
            calls.append((rows, on_conflict))
            return self

        def execute(self):
            return None

    class SeedClient:
        def table(self, name):
            assert name == "appliance_catalog"
            return SeedQuery()

    monkeypatch.setattr(seed_module, "get_supabase", lambda: SeedClient())

    assert seed_module.seed_catalog() == 44
    assert len(calls) == 1
    assert calls[0][1] == "id"
    assert len(calls[0][0]) == 44


def test_seed_fails_if_catalog_csv_is_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(seed_module, "configured_catalog_path", lambda: tmp_path / "missing.csv")

    with pytest.raises(FileNotFoundError, match="Catalog seed CSV not found"):
        seed_module.seed_catalog()
