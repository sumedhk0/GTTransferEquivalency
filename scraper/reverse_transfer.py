import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://oscar.gatech.edu/pls/bprod"
LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXY") + ["*", "l"]
REQUEST_DELAY = 0.3
MAX_RETRIES = 2

SCORECARD_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"
SCORECARD_SCHEMA_VERSION = 2
SCORECARD_CACHE = (
    Path.home() / ".cache" / "reverse_transfer" / f"scorecard_v{SCORECARD_SCHEMA_VERSION}.json"
)
SCORECARD_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
# Community college = IPEDS level 2 (2-year institution) AND public ownership.
CC_IPEDS_LEVEL = 2
CC_OWNERSHIP_PUBLIC = 1
CC_PREDOMINANT_DEGREE = 2  # kept for back-compat; no longer used for the CC check

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC", "PR", "VI", "GU", "AS", "MP",
}


def fetch(url, data, retries=MAX_RETRIES):
    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, data=data, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            if attempt < retries:
                time.sleep(1 * (attempt + 1))
            else:
                print(f"  Warning: failed to fetch {data}: {e}", file=sys.stderr)
                return None


def get_schools(letter):
    html = fetch(f"{BASE_URL}/wwtraneq.P_TranEq_Nme", {"letter": letter})
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", {"name": "sbgi_code"})
    if not select:
        return []
    schools = []
    for option in select.find_all("option"):
        code = option.get("value", "")
        name = option.get_text(strip=True)
        if code:
            schools.append((code, name))
    return schools


def get_equivalencies(letter, sbgi_code):
    html = fetch(f"{BASE_URL}/wwtraneq.P_TranEq_Rpt", {"letter": letter, "sbgi_code": sbgi_code})
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("div", class_="pagebodydiv")
    if not body:
        return []

    results = []
    tables = body.find_all("table", class_="datadisplaytable")

    for table in tables:
        ext_subj = ""
        ext_num = ""
        ext_title = ""
        bold_before = []

        prev = table
        while prev:
            prev = prev.previous_sibling
            if prev is None:
                break
            if hasattr(prev, "name") and prev.name == "table":
                break
            if hasattr(prev, "name") and prev.name == "b":
                tag_text = prev.get_text(strip=True)
                if tag_text == "Class Title:":
                    nxt = prev.next_sibling
                    while nxt:
                        if isinstance(nxt, str) and nxt.strip():
                            ext_title = nxt.strip()
                            break
                        if hasattr(nxt, "name") and nxt.name == "br":
                            break
                        nxt = nxt.next_sibling
                elif tag_text not in ("Level:", ""):
                    bold_before.insert(0, tag_text)

        if len(bold_before) >= 2:
            ext_subj = bold_before[0]
            ext_num = bold_before[1]

        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td", class_="dddefault")
            if len(cells) >= 4:
                gt_class_cell = cells[1]
                gt_title_cell = cells[2]
                gt_credits_cell = cells[3]

                bolds = gt_class_cell.find_all("b")
                if len(bolds) >= 2:
                    gt_subj = bolds[0].get_text(strip=True)
                    gt_num = bolds[1].get_text(strip=True)
                else:
                    continue

                gt_title = gt_title_cell.get_text(strip=True)
                gt_credits = gt_credits_cell.get_text(strip=True)

                results.append({
                    "ext_subj": ext_subj,
                    "ext_num": ext_num,
                    "ext_title": ext_title,
                    "gt_subj": gt_subj,
                    "gt_num": gt_num,
                    "gt_title": gt_title,
                    "gt_credits": gt_credits,
                })

    return results


def normalize_name(name):
    s = name.lower().strip()
    s = re.sub(r",\s*[a-z]{2}\s*$", "", s)  # drop trailing ", ST"
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\b(the|of|at)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _fetch_scorecard_all(api_key):
    fields = (
        "id,school.name,school.state,"
        "school.degrees_awarded.predominant,"
        "school.institutional_characteristics.level,"
        "school.ownership"
    )
    per_page = 100
    page = 0
    results = []
    while True:
        params = {
            "api_key": api_key,
            "fields": fields,
            "per_page": per_page,
            "page": page,
        }
        resp = requests.get(SCORECARD_URL, params=params, timeout=60)
        resp.raise_for_status()
        payload = resp.json()
        batch = payload.get("results", [])
        results.extend(batch)
        total = payload.get("metadata", {}).get("total", 0)
        print(
            f"  Fetched page {page + 1} ({len(results)}/{total}) from College Scorecard...",
            file=sys.stderr,
        )
        if (page + 1) * per_page >= total or not batch:
            break
        page += 1
    return results


def load_scorecard_index():
    if SCORECARD_CACHE.exists():
        age = time.time() - SCORECARD_CACHE.stat().st_mtime
        if age < SCORECARD_TTL_SECONDS:
            print("Using cached scorecard index.", file=sys.stderr)
            with SCORECARD_CACHE.open("r", encoding="utf-8") as f:
                return json.load(f)

    api_key = os.environ.get("COLLEGE_SCORECARD_API_KEY")
    if not api_key:
        sys.exit(
            "Error: --state/--community-college require a College Scorecard API key.\n"
            "Get a free key at https://api.data.gov/signup/ and set "
            "COLLEGE_SCORECARD_API_KEY in your environment."
        )

    print("Fetching College Scorecard index (first run may take a minute)...", file=sys.stderr)
    raw = _fetch_scorecard_all(api_key)

    index = {}
    for rec in raw:
        name = rec.get("school.name") or ""
        if not name:
            continue
        key = normalize_name(name)
        if not key:
            continue
        # First occurrence wins; duplicates are rare (multi-campus edge cases).
        index.setdefault(key, {
            "state": rec.get("school.state") or "",
            "predominant_degree": rec.get("school.degrees_awarded.predominant"),
            "level": rec.get("school.institutional_characteristics.level"),
            "ownership": rec.get("school.ownership"),
        })

    SCORECARD_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with SCORECARD_CACHE.open("w", encoding="utf-8") as f:
        json.dump(index, f)
    return index


def filter_schools(schools, index, state, cc_only, stats):
    out = []
    for code, name in schools:
        rec = index.get(normalize_name(name))
        if rec is None:
            stats["unmatched"] += 1
            continue
        if state and rec.get("state", "").upper() != state:
            continue
        if cc_only and not (
            rec.get("level") == CC_IPEDS_LEVEL
            and rec.get("ownership") == CC_OWNERSHIP_PUBLIC
        ):
            continue
        out.append((code, name))
    return out


def find_reverse_matches(target_subj, target_num, state=None, cc_only=False):
    matches = []
    total_letters = len(LETTERS)

    index = None
    stats = {"unmatched": 0}
    if state or cc_only:
        index = load_scorecard_index()

    for i, letter in enumerate(LETTERS, 1):
        schools = get_schools(letter)
        if index is not None:
            before = len(schools)
            schools = filter_schools(schools, index, state, cc_only, stats)
            print(
                f"[{letter}] {len(schools)}/{before} schools pass filters... "
                f"({i}/{total_letters} letters done)",
                file=sys.stderr,
            )
        else:
            print(
                f"[{letter}] Checking {len(schools)} schools... ({i}/{total_letters} letters done)",
                file=sys.stderr,
            )

        for school_code, school_name in schools:
            time.sleep(REQUEST_DELAY)
            equivs = get_equivalencies(letter, school_code)
            for eq in equivs:
                if eq["gt_subj"].upper() == target_subj.upper() and eq["gt_num"] == target_num:
                    matches.append({
                        "school": school_name,
                        "course": f"{eq['ext_subj']} {eq['ext_num']}",
                        "title": eq["ext_title"],
                        "gt_credits": eq["gt_credits"],
                    })
                    print(
                        f"school: {school_name}, "
                        f"course: {eq['ext_subj']} {eq['ext_num']}, "
                        f"title: {eq['ext_title']}, "
                        f"gt_credits: {eq['gt_credits']}"
                    )

    if index is not None and stats["unmatched"]:
        print(
            f"\nNote: {stats['unmatched']} OSCAR schools had no Scorecard match "
            "and were skipped.",
            file=sys.stderr,
        )

    return matches


def print_table(matches, target):
    if not matches:
        print(f"\nNo schools found with courses that transfer as {target}.")
        return

    headers = ["School", "Course", "Course Title", "GT Credits"]
    widths = [len(h) for h in headers]
    for m in matches:
        widths[0] = max(widths[0], len(m["school"]))
        widths[1] = max(widths[1], len(m["course"]))
        widths[2] = max(widths[2], len(m["title"]))
        widths[3] = max(widths[3], len(m["gt_credits"]))

    fmt = f"  {{:<{widths[0]}}}  {{:<{widths[1]}}}  {{:<{widths[2]}}}  {{:>{widths[3]}}}"
    sep = "  " + "  ".join("-" * w for w in widths)

    print(f"\nCourses that transfer as {target} ({len(matches)} found):\n")
    print(fmt.format(*headers))
    print(sep)
    for m in matches:
        print(fmt.format(m["school"], m["course"], m["title"], m["gt_credits"]))


def main():
    parser = argparse.ArgumentParser(
        description="Reverse lookup: find which schools have courses that transfer as a given GT course."
    )
    parser.add_argument("subject", help="GT course subject (e.g., CS)")
    parser.add_argument("number", help="GT course number (e.g., 1332)")
    parser.add_argument(
        "--state",
        help="Restrict results to schools in this 2-letter US state/territory code (e.g., CA).",
    )
    parser.add_argument(
        "--community-college",
        action="store_true",
        help="Restrict results to community colleges (predominantly associate's-granting).",
    )
    args = parser.parse_args()

    state = args.state.upper() if args.state else None
    if state and state not in US_STATES:
        parser.error(f"--state must be a 2-letter US state/territory code, got {args.state!r}")

    target = f"{args.subject.upper()} {args.number}"
    filter_desc = []
    if state:
        filter_desc.append(f"state={state}")
    if args.community_college:
        filter_desc.append("community_college=True")
    if filter_desc:
        print(f"Filters: {', '.join(filter_desc)}", file=sys.stderr)
    print(f"Searching for courses that transfer as {target}...\n", file=sys.stderr)

    matches = find_reverse_matches(
        args.subject, args.number, state=state, cc_only=args.community_college
    )
    matches.sort(key=lambda m: m["school"])
    print_table(matches, target)


if __name__ == "__main__":
    main()
