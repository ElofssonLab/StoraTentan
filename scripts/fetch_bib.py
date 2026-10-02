#!/usr/bin/env python3
"""Fetch BibTeX for every DOI in papers.tsv from Crossref and write references.bib.

Usage: python3 scripts/fetch_bib.py   (run from repository root)
Entries without DOI are kept in manual.bib and appended unchanged.
"""
import html, json, re, unicodedata, sys, time, urllib.error, urllib.parse, urllib.request
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


CONSORTIA = {"uniprot2023": "{The UniProt Consortium}", "go2023": "{The Gene Ontology Consortium}",
             "lander2001": "{International Human Genome Sequencing Consortium}",
             "encode2012": "{The ENCODE Project Consortium}"}


# Fields Crossref is missing for some records; inserted after the entry key.
EXTRA = {"saitou1987": "volume={4}, number={4}, pages={406--425},",
         "ferragina2000": "year={2000},",
         "broder1997": "year={1997},"}

# Typos in Crossref titles: (wrong, right).
TITLE_FIXES = [("prerequisitetto", "prerequisite to")]

# Author lists that Crossref has wrong or truncated.
AUTHORS = {
    "saitou1987": "Saitou, Naruya and Nei, Masatoshi",
    "encode2012": "{The ENCODE Project Consortium}",
    "altschul1997": "Altschul, Stephen F. and Madden, Thomas L. and Sch{\\\"a}ffer, Alejandro A. and Zhang, Jinghui"
                    " and Zhang, Zheng and Miller, Webb and Lipman, David J.",
    "berman2000": "Berman, Helen M. and Westbrook, John and Feng, Zukang and Gilliland, Gary and Bhat, T. N."
                  " and Weissig, Helge and Shindyalov, Ilya N. and Bourne, Philip E.",
    "lukashin1998": "Lukashin, Alexander V. and Borodovsky, Mark",
    "zhang2005": "Zhang, Yang and Skolnick, Jeffrey",
    "finn2006": "Finn, Robert D. and Mistry, Jaina and Schuster-B{\\\"o}ckler, Benjamin and Griffiths-Jones, Sam"
                " and Hollich, Volker and Lassmann, Timo and Moxon, Simon and Marshall, Mhairi and Khanna, Ajay"
                " and Durbin, Richard and Eddy, Sean R. and Sonnhammer, Erik L. L. and Bateman, Alex",
    "griffithsjones2003": "Griffiths-Jones, Sam and Bateman, Alex and Marshall, Mhairi and Khanna, Ajay"
                          " and Eddy, Sean R.",
    "katoh2002": "Katoh, Kazutaka and Misawa, Kazuharu and Kuma, Kei-ichi and Miyata, Takashi",
    "schaffer2001": "Sch{\\\"a}ffer, Alejandro A. and Aravind, L. and Madden, Thomas L. and Shavirin, Sergei"
                    " and Spouge, John L. and Wolf, Yuri I. and Koonin, Eugene V. and Altschul, Stephen F.",
    "wang1994": "Wang, Lusheng and Jiang, Tao",
    "bohm1994": "B{\\\"o}hm, Hans-Joachim",
}


def clean(bib, key):
    """Fix common Crossref quirks: markup in titles, editor notes, empty consortium authors."""
    bib = re.sub(r"</?(i|b|tt|scp|sub|sup)>", "", bib)
    bib = re.sub(r"\s*1?\s*1\s*Edited by [^}]*", "", bib)
    bib = re.sub(r"\s+", " ", bib)
    bib = unicodedata.normalize("NFC", bib).replace("\u2010", "-")
    bib = html.unescape(bib).replace(" & ", " \\& ")
    bib = bib.replace("author={van Kempen,", "author={{van Kempen},")
    bib = re.sub(r",? month=\w+(?=,| })", "", bib)
    bib = bib.replace("author={ and ", "author={" + CONSORTIA.get(key, "") + (" and " if key in CONSORTIA else ""), 1)
    for wrong, right in TITLE_FIXES:
        bib = bib.replace(wrong, right)
    bib = re.sub(r" editor=\{[^}]*\},", "", bib)
    if key in AUTHORS:
        bib = re.sub(r" author=\{(?:[^{}]|\{[^{}]*\})*\},", "", bib)
        bib = bib.replace(f"{{{key},", f"{{{key}, author={{{AUTHORS[key]}}},", 1)
    if key in EXTRA:
        bib = bib.replace(f"{{{key},", f"{{{key}, {EXTRA[key]}", 1)
    return bib


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
        entries.append(clean(bib, key))
        print(f"{key}\t{res['author']}\t{res['year']}\t{res['title'][:90]}")
    if MANUAL.exists():
        entries.append(MANUAL.read_text().strip())
    OUT.write_text("\n\n".join(entries) + "\n")
    for f in failed:
        print("FAILED", *f, file=sys.stderr)


if __name__ == "__main__":
    main()
