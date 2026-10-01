#!/usr/bin/env python3
"""Fetch BibTeX for every DOI in papers.tsv from Crossref and write references.bib.

Usage: python3 scripts/fetch_bib.py   (run from repository root)
Entries without DOI are kept in manual.bib and appended unchanged.
"""
import json, re, sys, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / "scripts" / "papers.tsv"
MANUAL = ROOT / "scripts" / "manual.bib"
OUT = ROOT / "references.bib"
CACHE = ROOT / "scripts" / ".bibcache"
CACHE.mkdir(exist_ok=True)


def get(url, accept, tries=6):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "StoraTentan-bib/1.0"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                time.sleep(0.5)
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == tries - 1:
                raise
            time.sleep(2 ** i)


def fetch(key, doi):
    cache = CACHE / f"{key}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    q = urllib.parse.quote(doi, safe="")
    try:
        meta = json.loads(get(f"https://api.crossref.org/works/{q}", "application/json"))["message"]
        bib = get(f"https://api.crossref.org/works/{q}/transform/application/x-bibtex", "application/x-bibtex")
        res = {"ok": True, "title": (meta.get("title") or [""])[0],
               "author": (meta.get("author") or [{}])[0].get("family", ""),
               "year": (meta.get("issued", {}).get("date-parts") or [[None]])[0][0], "bib": bib}
    except Exception as e:  # noqa: BLE001
        res = {"ok": False, "error": str(e)}
    if res["ok"]:
        cache.write_text(json.dumps(res))
    return res


def main():
    rows = [l.split("\t") for l in TSV.read_text().splitlines() if l.strip() and not l.startswith("#")]
    with ThreadPoolExecutor(1) as ex:
        results = list(ex.map(lambda r: fetch(r[0], r[1].strip()), rows))
    entries, failed = [], []
    for (key, doi), res in zip(rows, results):
        if not res["ok"]:
            failed.append((key, doi, res["error"]))
            continue
        bib = re.sub(r"^\s*@(\w+)\{[^,]*,", lambda m: f"@{m.group(1)}{{{key},", res["bib"].strip(), count=1)
        entries.append(bib)
        print(f"{key}\t{res['author']}\t{res['year']}\t{res['title'][:90]}")
    if MANUAL.exists():
        entries.append(MANUAL.read_text().strip())
    OUT.write_text("\n\n".join(entries) + "\n")
    for f in failed:
        print("FAILED", *f, file=sys.stderr)


if __name__ == "__main__":
    main()
