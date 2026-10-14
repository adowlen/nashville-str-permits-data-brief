"""LAYER B - property type via assessor join (verification pass addition).

Joins current (ISSUED) STR permits to Metro Nashville's Parcels view
(ArcGIS, same open-data org as the permit file) on permit Parcel ==
assessor STANPAR, and tallies the assessor land-use description
(LUDesc) for each permit's parcel. Reports the join match rate and the
permit-weighted land-use split, overall, for the investor class, and
for the two largest permit holders.

Output: layer_property_type_results.json + printed summary.
"""
import csv
import json
import os
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "data", "nashville_str_permits_2026-10-13.csv"),
                                newline="", encoding="utf-8-sig")))
CODE = {"CAZ10A001": "OO", "CAZ10A002": "NOO", "CAZ10A003": "NOO"}
issued = [r for r in rows if r["Permit_Status"] == "ISSUED"]
parcels = sorted({r["Parcel"].strip() for r in issued if r["Parcel"].strip()})

SVC = ("https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/"
       "Parcels_view/FeatureServer/0/query")

def fetch(where):
    url = SVC + "?" + urllib.parse.urlencode({
        "where": where, "outFields": "STANPAR,LUCode,LUDesc",
        "returnGeometry": "false", "f": "json", "resultRecordCount": 2000})
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as fh:
                return json.load(fh)
        except Exception as exc:  # noqa: BLE001 - retry transient server drops
            last = exc
            import time
            time.sleep(3 * (attempt + 1))
    raise SystemExit(f"query failed after retries: {last}")

lu = {}
multi = Counter()
failed_parcels = []
BATCH = 50  # server 404s GET queries somewhere between 87 and 100 IN values; 50 is fast and safe

def fetch_chunk(chunk):
    in_list = ",".join("'" + p.replace("'", "''") + "'" for p in chunk)
    d = fetch(f"STANPAR IN ({in_list})")
    if "error" in d:
        if len(chunk) == 1:
            failed_parcels.extend(chunk)
            return
        mid = len(chunk) // 2
        fetch_chunk(chunk[:mid])
        fetch_chunk(chunk[mid:])
        return
    for f in d.get("features", []):
        a = f["attributes"]
        sp = a["STANPAR"]
        if sp in lu and lu[sp] != (a["LUCode"], a["LUDesc"]):
            multi[sp] += 1
        lu[sp] = (a["LUCode"], a["LUDesc"])

for i in range(0, len(parcels), BATCH):
    fetch_chunk(parcels[i:i + BATCH])
    print(f"batch {i}: cumulative matched parcels {len(lu)}", flush=True)

matched_permits = [r for r in issued if r["Parcel"].strip() in lu]
OUT = {
    "distinct_current_parcels_requested": len(parcels),
    "distinct_parcels_matched": len(lu),
    "parcel_match_rate_pct": round(100 * len(lu) / len(parcels), 2),
    "current_permits": len(issued),
    "current_permits_matched": len(matched_permits),
    "permit_match_rate_pct": round(100 * len(matched_permits) / len(issued), 2),
    "stanpar_with_conflicting_ludesc": int(sum(1 for v in multi.values() if v)),
    "ludesc_distribution_current_permits": Counter(
        lu[r["Parcel"].strip()][1] for r in matched_permits).most_common(),
    "ludesc_distribution_current_parcels": Counter(v[1] for v in lu.values()).most_common(),
}

def bucket(desc):
    d = (desc or "").upper()
    if "CONDO" in d:
        return "condo"
    if "SINGLE FAM" in d:
        return "single_family"
    if ("APARTMENT" in d or "APT" in d or "MULTI" in d or "DUPLEX" in d
            or "TRIPLEX" in d or "QUAD" in d):
        return "multifamily_apartment"
    if "HOTEL" in d or "MOTEL" in d:
        return "hotel_motel"
    return "other:" + d

OUT["desc_bucket_audit"] = {
    desc: bucket(desc)
    for desc, _ in Counter(lu[r["Parcel"].strip()][1] for r in matched_permits).most_common()}
OUT["failed_parcels"] = failed_parcels

for label, frame in [
        ("all_current", matched_permits),
        ("investor_noo", [r for r in matched_permits if CODE[r["Permit_SubType"].strip()] == "NOO"]),
        ("owner_occupied", [r for r in matched_permits if CODE[r["Permit_SubType"].strip()] == "OO"])]:
    c = Counter(bucket(lu[r["Parcel"].strip()][1]) for r in frame)
    OUT[f"bucket_{label}"] = {"n": len(frame),
                              "by_bucket": {k: c[k] for k in sorted(c)},
                              "pct": {k: round(100 * c[k] / len(frame), 1) for k in sorted(c)}}

# top-2 holders' property-type mix (builder normalization reimplemented)
import re
SUFFIXES = {"LLC", "INC", "CORP", "COMPANY", "LTD", "LP", "LLP", "CO"}
def key_builder(name):
    s = re.sub(r"[^A-Z0-9 ]", " ", str(name).upper())
    parts = [p for p in s.split() if p]
    while parts and parts[-1] in SUFFIXES:
        parts.pop()
    return " ".join(parts)
for holder in ["BOP NEST NASHVILLE", "SIXTH SOUTH PARTNERS"]:
    recs = [r for r in matched_permits if key_builder(r["Permit_Owner_Name"]) == holder]
    c = Counter(bucket(lu[r["Parcel"].strip()][1]) for r in recs)
    OUT[f"holder_{holder}"] = {"matched_permits": len(recs),
                                "by_bucket": dict(c),
                                "top_ludesc": Counter(lu[r["Parcel"].strip()][1] for r in recs).most_common(5)}

# unmatched parcels sample (for the match-rate honesty note)
unmatched = [p for p in parcels if p not in lu]
OUT["unmatched_parcel_sample"] = unmatched[:15]
OUT["unmatched_parcel_suffix_CO_share"] = round(
    100 * sum(1 for p in unmatched if p.endswith("CO")) / len(unmatched), 1) if unmatched else None
OUT["all_parcel_suffix_CO_share"] = round(
    100 * sum(1 for p in parcels if p.endswith("CO")) / len(parcels), 1)

with open(os.path.join(HERE, "layer_property_type_results.json"), "w") as fh:
    json.dump(OUT, fh, indent=1, default=str)
print(json.dumps(OUT, indent=1, default=str))
