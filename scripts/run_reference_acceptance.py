"""Read-only comparison of supplied references; default pack is explicitly blocked."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lv_assist.catalog_validation import catalog_object
from lv_assist.reference_acceptance import evaluate_pack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, default=ROOT / 'tests/reference_cases/pending.json')
    args = parser.parse_args()
    try:
        result = evaluate_pack(catalog_object(args.pack.read_text(encoding='utf-8')))
    except (ValueError, OSError, TypeError) as error:
        result = {'status': 'ERROR', 'engineering_verification': 'NOT_VERIFIED', 'reason': str(error)}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return {'MATCH': 0, 'DIFFERENCE': 1, 'ERROR': 1, 'BLOCKED': 2}[result['status']]


if __name__ == '__main__':
    raise SystemExit(main())
