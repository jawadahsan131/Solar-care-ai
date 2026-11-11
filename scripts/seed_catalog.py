from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.db import get_supabase  # noqa: E402
from app.services.appliances import configured_catalog_path  # noqa: E402
from app.services.catalog import load_catalog  # noqa: E402

BATCH_SIZE = 100


def _database_row(catalog_row: dict) -> dict:
    stable_id = uuid5(
        NAMESPACE_URL,
        json.dumps(catalog_row, sort_keys=True, separators=(",", ":")),
    )
    return {"id": str(stable_id), **catalog_row}


def seed_catalog() -> int:
    path = configured_catalog_path()
    if not path.is_file():
        raise FileNotFoundError(f"Catalog seed CSV not found: {path}")
    rows = load_catalog(path)
    client = get_supabase()
    database_rows = [_database_row(row) for row in rows]
    for offset in range(0, len(database_rows), BATCH_SIZE):
        client.table("appliance_catalog").upsert(
            database_rows[offset : offset + BATCH_SIZE],
            on_conflict="id",
        ).execute()
    return len(database_rows)


def main() -> None:
    count = seed_catalog()
    print(f"Upserted {count} catalog rows into public.appliance_catalog.")


if __name__ == "__main__":
    main()
