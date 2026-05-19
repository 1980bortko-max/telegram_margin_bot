# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import tempfile
from typing import Dict, Iterable, Tuple


SMOKE_CASE_DATA: Dict[str, Dict[str, str]] = {
    "k2-engine-oil-0w40": {
        "brand": "K2",
        "liquid_type": "ENGINE OIL",
        "viscosity": "0W-40",
    },
    "castrol-engine-oil-0w40-1l": {
        "brand": "CASTROL",
        "liquid_type": "ENGINE OIL",
        "viscosity": "0W-40",
        "volume_from": "1",
        "volume_to": "1",
    },
    "export-silver-castrol-engine-oil-0w40-1l": {
        "client_group": "EXPORT Silver/1,35 1.35",
        "brand": "CASTROL",
        "liquid_type": "ENGINE OIL",
        "viscosity": "0W-40",
        "volume_from": "1",
        "volume_to": "1",
    },
    "article-15f030": {
        "article": "15F030",
    },
}


def iter_cases(selected: str, filters_cls) -> Iterable[Tuple[str, object]]:
    if selected == "all":
        return [(name, filters_cls.from_dict(data)) for name, data in SMOKE_CASE_DATA.items()]
    return [(selected, filters_cls.from_dict(SMOKE_CASE_DATA[selected]))]


def main() -> int:
    parser = argparse.ArgumentParser(description="Headless smoke tests for Autofun CRM liquids search")
    parser.add_argument(
        "case",
        choices=["all", *SMOKE_CASE_DATA.keys()],
        help="Smoke case to run",
    )
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument(
        "--profile-dir",
        default="",
        help="Chrome profile directory. Defaults to a unique temporary smoke profile.",
    )
    args = parser.parse_args()

    profile_dir = args.profile_dir or tempfile.mkdtemp(prefix="crm_chrome_profile_smoke_")
    os.environ["CATALOG_CHROME_PROFILE_DIR"] = profile_dir

    from .crm_session import reset_crm_session
    from .liquids_search import LiquidsFilters, search_liquids_with_report
    from .runtime_settings import set_catalog_search_headless

    set_catalog_search_headless(True)
    failed = False

    print(f"Chrome profile: {profile_dir}", flush=True)

    for name, filters in iter_cases(args.case, LiquidsFilters):
        print(f"=== {name} ===", flush=True)
        try:
            result = search_liquids_with_report(filters, limit=args.limit)
        except Exception as exc:
            failed = True
            print(f"FAIL: {exc}", flush=True)
            continue

        print(f"requested: {result.report.requested}", flush=True)
        print(f"applied: {result.report.applied}", flush=True)
        print(f"skipped: {result.report.skipped}", flush=True)
        print(f"products: {len(result.products)}", flush=True)

        if not result.products:
            failed = True
            print("FAIL: no products returned", flush=True)
        else:
            print("OK", flush=True)

    reset_crm_session()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
