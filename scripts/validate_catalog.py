"""Read-only catalog checks. A successful check is not engineering sign-off."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lv_assist.catalog_validation import validate_catalog_database


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "lv_assist/data/lv_assist.db")
    args = parser.parse_args()
    try:
        result = validate_catalog_database(args.db)
    except (ValueError, OSError, sqlite3.DatabaseError) as error:
        print(json.dumps({"status": "INVALID", "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "STRUCTURALLY_VALID", **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
