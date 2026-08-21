"""One-command data refresh for the San Pedro Ledger, with verification gates.

Runs every fetcher, rebuilds derived tables, re-runs the ledger export, and
(optionally) injects the fresh DATA into the ledger HTML — refusing to proceed
when anything looks wrong. Designed so "refresh the ledger" is a five-minute
supervised run, and so silent breakage (schema drift, analyte renames, shrinking
tables) fails loudly instead of publishing garbage.

Usage (from the repo root, inside the venv):
    .venv/bin/python3 pipeline/refresh.py                      # full fetch + export + gates
    .venv/bin/python3 pipeline/refresh.py --skip-fetch         # export + gates only
    .venv/bin/python3 pipeline/refresh.py --inject             # also inject into the ledger HTML
    .venv/bin/python3 pipeline/refresh.py --export PATH --html PATH   # override locations

Publishing the artifact remains a session action, after reviewing the change
summary this script prints.
"""

import argparse
import io
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
DB.parent.mkdir(parents=True, exist_ok=True)  # cold start: data/ is gitignored
PY = sys.executable
PIPE = ROOT / "pipeline"

# Canonical locations: both live in the repo. The committed
# pipeline/ledger_data.json is the durable gate baseline (series may never
# shrink relative to it), which also makes cold-start CI runs fully guarded.
DEFAULT_EXPORT = PIPE / "export_ledger.py"
DEFAULT_HTML = ROOT / "docs" / "index.html"

LMWQ_PAGE = "https://www.lindamarwaterquality.org/test-results"
SSO_BASE = "https://www.waterboards.ca.gov/water_issues/programs/sso/docs/data_files/"
SSO_FILES = {"sso_pacifica_old": "SSO.txt", "sso_pacifica_new": "Cat1-2-3-Spills.txt"}
WDID = "2SSO10100"

# Schema-drift expectations. New values WARN (county adding enterococcus at the
# creek in 2026 is the precedent); lmwq analytes outside the mapping FAIL,
# because the export would silently drop them.
CEDEN_EXPECTED_ANALYTES = {"E. coli", "Enterococcus", "Coliform, Total", "Coliform, Fecal"}
LMWQ_EXPECTED_ANALYTES = {"ecoli", "ent"}

GATE_TABLES = ["ceden_raw", "lmwq_long", "bwtf_lindamar", "tide_hourly",
               "weather_daily", "wx_extra_daily", "rain_context",
               "sso_pacifica_old", "sso_pacifica_new"]

FAILURES: list[str] = []
WARNINGS: list[str] = []


def fail(msg):
    FAILURES.append(msg)
    print(f"  GATE FAIL: {msg}")


def warn(msg):
    WARNINGS.append(msg)
    print(f"  warn: {msg}")


def table_counts():
    con = sqlite3.connect(DB)
    out = {}
    for t in GATE_TABLES:
        try:
            out[t] = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        except sqlite3.OperationalError:
            out[t] = None
    con.close()
    return out


def run_script(name):
    print(f"-- {name}")
    r = subprocess.run([PY, str(PIPE / name)], cwd=ROOT, capture_output=True, text=True)
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-4:])
    print("   " + tail.replace("\n", "\n   ") if tail else "   (no output)")
    if r.returncode != 0:
        fail(f"{name} exited {r.returncode}")


def download_lmwq():
    """Scrape the Coalition's test-results page for the two xlsx links (URLs
    change with every upload) and download them to the paths parse_lmwq expects."""
    print("-- coalition xlsx (scrape + download)")
    page = requests.get(LMWQ_PAGE, timeout=60).text
    links = list(dict.fromkeys(re.findall(r'https://[^"\'\s]+\.xlsx[^"\'\s]*', page)))
    if len(links) < 2:
        fail(f"expected 2 xlsx links on {LMWQ_PAGE}, found {len(links)}")
        return
    # Wix file URLs are opaque — identify each workbook by sniffing its contents.
    def sniff(url):
        blob = requests.get(url, timeout=120).content
        xl = pd.ExcelFile(io.BytesIO(blob))
        text = " ".join(xl.sheet_names)
        for sheet in xl.sheet_names[:3]:
            head = xl.parse(sheet, nrows=3, header=None)
            text += " " + " ".join(str(v) for v in head.values.ravel())
        is_ent = bool(re.search(r"entero", text, re.I))
        is_eco = bool(re.search(r"e\.?\s?_?-?coli", text, re.I))
        return blob, is_ent, is_eco
    found = {}
    for url in links[:4]:
        try:
            blob, is_ent, is_eco = sniff(url)
        except Exception as e:
            warn(f"could not read {url.split('/')[-1][:40]}: {e}")
            continue
        if is_ent and not is_eco and "enterococcus.xlsx" not in found:
            found["enterococcus.xlsx"] = blob
        elif is_eco and not is_ent and "ecoli.xlsx" not in found:
            found["ecoli.xlsx"] = blob
    if len(found) < 2:
        fail(f"content-sniff could not identify both workbooks on {LMWQ_PAGE} "
             f"({len(links)} links, identified: {sorted(found)})")
        return
    dest = ROOT / "data" / "lmwq"
    dest.mkdir(parents=True, exist_ok=True)
    for name, blob in found.items():
        p = dest / name
        if p.exists():
            shutil.copy2(p, p.with_suffix(".xlsx.prev"))
        p.write_bytes(blob)
        print(f"   {name}: identified by content ({len(blob)//1024} KB)")


def fetch_sso():
    """Refresh the CIWQS spill tables (flat files, latin-1, tab-delimited),
    filtered to Pacifica's WDID."""
    print("-- CIWQS spill files")
    con = sqlite3.connect(DB)
    for table, fname in SSO_FILES.items():
        try:
            raw = requests.get(SSO_BASE + fname, timeout=180).content
            df = pd.read_csv(io.BytesIO(raw), sep="\t", encoding="latin-1",
                             low_memory=False, on_bad_lines="skip")
            wcol = [c for c in df.columns if c.strip().upper() == "WDID"]
            if not wcol:
                fail(f"{fname}: no WDID column (columns changed?)")
                continue
            sub = df[df[wcol[0]].astype(str).str.strip() == WDID]
            try:
                prev = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            except sqlite3.OperationalError:
                prev = 0  # cold start: no baseline table yet
            if len(sub) < prev:
                fail(f"{table}: fetched {len(sub)} rows < existing {prev} — refusing to shrink")
                continue
            sub.to_sql(table, con, if_exists="replace", index=False)
            print(f"   {table}: {prev} -> {len(sub)} rows")
        except requests.RequestException as e:
            warn(f"{fname}: fetch failed ({e}) — keeping existing table")
    con.close()


def analyte_drift():
    print("-- schema drift checks")
    con = sqlite3.connect(DB)
    ceden = {r[0] for r in con.execute("SELECT DISTINCT Analyte FROM ceden_raw")}
    new = ceden - CEDEN_EXPECTED_ANALYTES
    if new:
        warn(f"CEDEN has new analyte(s) {sorted(new)} — decide whether the ledger should carry them")
    lmwq = {r[0] for r in con.execute("SELECT DISTINCT analyte FROM lmwq_long WHERE value IS NOT NULL")}
    unmapped = lmwq - LMWQ_EXPECTED_ANALYTES
    if unmapped:
        fail(f"lmwq_long analyte(s) {sorted(unmapped)} not in the export mapping — export would drop them")
    con.close()


def run_export(export_path: Path):
    print(f"-- export ({export_path})")
    out_json = export_path.parent / "ledger_data.json"
    prev = {}
    if out_json.exists():
        d = json.loads(out_json.read_text())
        prev = {k: len(v) for k, v in d.items() if isinstance(v, list)}
    r = subprocess.run([PY, str(export_path)], capture_output=True, text=True)
    print("   " + r.stdout.strip().replace("\n", "\n   "))
    if r.returncode != 0:
        fail(f"export exited {r.returncode}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else ''}")
        return None
    d = json.loads(out_json.read_text())
    for key in ["daily", "creek", "beach", "spills", "sites", "bwtf"]:
        if key not in d:
            fail(f"export output missing series '{key}'")
    if len(d.get("geo", {})) != 5:
        fail(f"geo has {len(d.get('geo', {}))} stations, expected 5 (LMMS/ADMS/PRLT/SPCM/LM5)")
    for k, n_prev in prev.items():
        n_new = len(d.get(k, []))
        if n_new < n_prev:
            fail(f"series '{k}' shrank: {n_prev} -> {n_new}")
    if sum(1 for row in d.get("creek", []) if "ent" in row) < 4:
        fail("creek enterococcus attachments < 4 (spring-2026 samples lost?)")
    if sum(1 for row in d.get("sites", []) if row.get("ec") is not None) < 344:
        fail("coalition E. coli in sites < 344 (the 'ecoli' analyte mapping regressed?)")
    d["built"] = date.today().isoformat()
    out_json.write_text(json.dumps(d, separators=(",", ":"), allow_nan=False))
    changes = {k: (len(d.get(k, [])) - prev.get(k, 0)) for k in prev} if prev else {}
    return d, changes


def inject(html_path: Path, out_json: Path):
    print(f"-- inject ({html_path})")
    s = html_path.read_text(encoding="utf-8")
    i0 = s.index("const DATA = ")
    i1 = s.index("\n", i0)
    if s[i1 - 1] != ";":
        fail("DATA line does not end with ';' — HTML layout changed, not injecting")
        return
    shutil.copy2(html_path, html_path.with_suffix(".html.bak"))
    s = s[:i0] + "const DATA = " + out_json.read_text(encoding="utf-8") + ";" + s[i1:]
    html_path.write_text(s, encoding="utf-8")
    m = re.findall(r"<script>(.*?)</script>", s, re.S)
    ck = html_path.parent / "_refresh_ck.js"
    ck.write_text(m[-1], encoding="utf-8")
    r = subprocess.run(["node", "--check", str(ck)], capture_output=True, text=True)
    if r.returncode != 0:
        fail(f"node --check failed after inject: {r.stderr.strip()[:200]} — restore from .bak")
    else:
        print("   injected + syntax OK (backup at .html.bak)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-fetch", action="store_true", help="skip source fetches; export + gates only")
    ap.add_argument("--inject", action="store_true", help="inject fresh DATA into the ledger HTML")
    ap.add_argument("--export", type=Path, default=DEFAULT_EXPORT)
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    a = ap.parse_args()

    if not a.export.exists():
        sys.exit(f"export script not found at {a.export} — pass --export (has the working copy moved?)")

    before = table_counts()
    if not a.skip_fetch:
        download_lmwq()
        run_script("parse_lmwq.py")
        run_script("fetch.py")
        run_script("fetch_bwtf.py")
        run_script("fetch_covariates.py")
        run_script("features.py")
        fetch_sso()
        after = table_counts()
        print("-- table deltas")
        for t in GATE_TABLES:
            b, n = before.get(t), after.get(t)
            if n is None:
                warn(f"{t}: missing after fetch")
                continue
            if b is None:
                print(f"   {t}: (cold start) {n} rows")
                continue
            if n < b:
                fail(f"{t} shrank: {b} -> {n}")
            else:
                print(f"   {t}: {b} -> {n} (+{n - b})")
        analyte_drift()

    result = None
    if not FAILURES:
        result = run_export(a.export)

    if result and a.inject and not FAILURES:
        inject(a.html, a.export.parent / "ledger_data.json")

    print("\n== SUMMARY ==")
    if result:
        d, changes = result
        lasts = {k: d[k][-1]["d"] for k in ["creek", "beach", "sites", "bwtf"] if d.get(k)}
        print("  data through: " + " · ".join(f"{k} {v}" for k, v in lasts.items()))
        if changes:
            grew = {k: v for k, v in changes.items() if v}
            print("  new rows: " + (", ".join(f"{k} +{v}" for k, v in grew.items()) if grew else "none"))
    for w in WARNINGS:
        print(f"  WARN: {w}")
    if FAILURES:
        print(f"  {len(FAILURES)} GATE FAILURE(S) — nothing was injected. Review before publishing:")
        for f in FAILURES:
            print(f"    - {f}")
        sys.exit(1)
    print("  all gates passed." + ("" if a.inject else " (no --inject: HTML untouched)"))
    print("  publish remains a session action: review the summary, then republish the artifact.")


if __name__ == "__main__":
    main()
