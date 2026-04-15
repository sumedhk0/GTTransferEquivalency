"""Nightly scraper: produces site/data.json from OSCAR + College Scorecard."""
import datetime as dt
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from scraper.reverse_transfer import (
    CC_IPEDS_LEVEL,
    CC_OWNERSHIP_PUBLIC,
    LETTERS,
    REQUEST_DELAY,
    get_equivalencies,
    get_schools,
    load_scorecard_index,
    normalize_name,
)

OUTPUT = Path(__file__).resolve().parent.parent / "site" / "data.json"
MAX_FAILURE_RATE = 0.10


def scrape_all():
    index = load_scorecard_index()

    schools_by_code = {}
    courses_by_code = defaultdict(list)
    seen_codes = set()
    attempts = 0
    failures = 0

    for i, letter in enumerate(LETTERS, 1):
        schools = get_schools(letter)
        print(f"[{letter}] {len(schools)} schools ({i}/{len(LETTERS)})", file=sys.stderr)
        for code, name in schools:
            if code in seen_codes:
                continue
            seen_codes.add(code)
            attempts += 1
            time.sleep(REQUEST_DELAY)
            try:
                equivs = get_equivalencies(letter, code)
            except Exception as e:
                failures += 1
                print(f"  FAIL {code} {name}: {e}", file=sys.stderr)
                continue

            rec = index.get(normalize_name(name))
            state = (rec or {}).get("state") or None
            if rec is not None:
                is_cc = (
                    rec.get("level") == CC_IPEDS_LEVEL
                    and rec.get("ownership") == CC_OWNERSHIP_PUBLIC
                )
            else:
                is_cc = None

            schools_by_code[code] = {
                "code": code,
                "name": name,
                "state": state,
                "is_community_college": is_cc,
            }
            for eq in equivs:
                courses_by_code[code].append({
                    "ext_subj": eq["ext_subj"],
                    "ext_num": eq["ext_num"],
                    "ext_title": eq["ext_title"],
                    "gt_subj": eq["gt_subj"],
                    "gt_num": eq["gt_num"],
                    "gt_credits": eq["gt_credits"],
                })

    schools_out = []
    for code, meta in sorted(schools_by_code.items(), key=lambda kv: kv[1]["name"].lower()):
        meta["courses"] = courses_by_code.get(code, [])
        schools_out.append(meta)

    failure_rate = failures / attempts if attempts else 0
    print(
        f"\nDone: {attempts} schools attempted, {failures} failed "
        f"({failure_rate:.1%}).",
        file=sys.stderr,
    )

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schools": schools_out,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"), ensure_ascii=False)
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)", file=sys.stderr)

    if failure_rate > MAX_FAILURE_RATE:
        sys.exit(f"Failure rate {failure_rate:.1%} exceeded {MAX_FAILURE_RATE:.0%} threshold")


if __name__ == "__main__":
    scrape_all()
