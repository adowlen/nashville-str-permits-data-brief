"""LAYER A - STR density per housing unit + county-footprint sensitivity.

Layered data (both U.S. Census Bureau, no API key needed):
1. ACS 2024 5-year estimates, table B25001 (total housing units),
   ZCTA level, from the official table-based summary file
   (acsdt5y2024-b25001.dat). api.census.gov itself is key-gated as of
   this pull (keyless requests redirect to a missing-key page), so the
   summary file is the access route.
2. 2020 Census ZCTA-to-county relationship file
   (tab20_zcta520_county20_natl.txt): land area of each ZCTA inside
   Davidson County (FIPS 47037) vs the ZCTA's total land area, used to
   re-run the brief's outside-county test under Census-defined
   footprints.

Outputs: layer_density_results.json + printed summary.
"""
import csv
import io
import json
import os
import re
import urllib.request
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "data", "nashville_str_permits_2026-10-13.csv"),
                                newline="", encoding="utf-8-sig")))
CODE = {"CAZ10A001": "OO", "CAZ10A002": "NOO", "CAZ10A003": "NOO"}
issued = [r for r in rows if r["Permit_Status"] == "ISSUED"]
noo = [r for r in issued if CODE[r["Permit_SubType"].strip()] == "NOO"]
oo = [r for r in issued if CODE[r["Permit_SubType"].strip()] == "OO"]
prop_zip_counts = Counter(r["ZIP"].strip() for r in issued)
PROP_ZIPS = sorted({r["ZIP"].strip() for r in rows})

OUT = {"acs_vintage": "ACS 2024 5-year (2020-2024), table B25001, summary file acsdt5y2024-b25001.dat",
       "acs_api_note": "api.census.gov redirected keyless queries to a missing-key page on 2026-10-13; the official summary file was used instead."}

# ---- 1. ACS housing units for the ZCTAs we need ----
SF = ("https://www2.census.gov/programs-surveys/acs/summary_file/2024/"
      "table-based-SF/data/5YRData/acsdt5y2024-b25001.dat")
need = set(PROP_ZIPS) | {r["Permit_Owner_Zip"].strip()[:5] for r in issued}
hu = {}
with urllib.request.urlopen(SF, timeout=180) as fh:
    text = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
    rd = csv.reader(text, delimiter="|")
    header = next(rd)
    gi, ei = header.index("GEO_ID"), header.index("B25001_E001")
    for rec in rd:
        gid = rec[gi]
        if gid.startswith("860Z200US"):
            z = gid[-5:]
            if z in need:
                try:
                    hu[z] = int(rec[ei])
                except ValueError:
                    pass
OUT["acs_hu_found_for_needed_zctas"] = len(hu)

# ---- 2. ZCTA land-area share inside Davidson County ----
rel_url = ("https://www2.census.gov/geo/docs/maps-data/data/rel2020/"
           "zcta520/tab20_zcta520_county20_natl.txt")
land_part = {}
with urllib.request.urlopen(rel_url, timeout=180) as fh:
    text = io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace")
    for r in csv.DictReader(text, delimiter="|"):
        z = r["GEOID_ZCTA5_20"]
        total = int(r["AREALAND_ZCTA5_20"] or 0)
        part = int(r["AREALAND_PART"] or 0) if r["GEOID_COUNTY_20"] == "47037" else 0
        if z not in land_part:
            land_part[z] = [0, total]
        land_part[z][0] += part

def davidson_land_share(z):
    if z not in land_part or land_part[z][1] == 0:
        return None
    return land_part[z][0] / land_part[z][1]

# ---- 3. density table ----
density = []
for z, n in prop_zip_counts.most_common():
    u = hu.get(z)
    density.append({
        "zip": z, "current_permits": n, "acs2024_housing_units": u,
        "permits_per_1000_hu": round(1000 * n / u, 1) if u else None,
        "davidson_land_share_pct": (round(100 * davidson_land_share(z), 1)
                                    if davidson_land_share(z) is not None else None),
        "share_of_current_permits_pct": round(100 * n / len(issued), 1),
    })
OUT["density_by_property_zip"] = density
m_permits = sum(d["current_permits"] for d in density if d["acs2024_housing_units"])
m_hu = sum(d["acs2024_housing_units"] for d in density if d["acs2024_housing_units"])
OUT["density_coverage"] = {"permits": m_permits, "housing_units": m_hu,
                           "overall_per_1000": round(1000 * m_permits / m_hu, 1)}

# ---- 4. footprint sensitivity ----
def ozip(r):
    z = r["Permit_Owner_Zip"].strip()[:5]
    return z if re.fullmatch(r"\d{5}", z or "") else ""

def share_outside(frame, is_outside, label):
    base = [r for r in frame if ozip(r)]
    out = sum(1 for r in base if is_outside(ozip(r)))
    return {"label": label, "base": len(base), "outside_n": out,
            "outside_pct": round(100 * out / len(base), 2) if base else None}

OUT["footprint_variants_current_noo"] = [
    share_outside(noo, lambda z: z not in PROP_ZIPS, "brief: file property-ZIP footprint"),
    share_outside(noo, lambda z: (davidson_land_share(z) or 0) == 0, "census: ZCTA has no Davidson land"),
    share_outside(noo, lambda z: (davidson_land_share(z) or 0) < 0.5, "census: ZCTA under 50 pct Davidson land"),
]
OUT["footprint_variants_current_oo_control"] = [
    share_outside(oo, lambda z: z not in PROP_ZIPS, "brief: file property-ZIP footprint"),
    share_outside(oo, lambda z: (davidson_land_share(z) or 0) < 0.5, "census: ZCTA under 50 pct Davidson land"),
]
OUT["property_footprint_zip_davidson_land_share_pct"] = {
    z: (round(100 * davidson_land_share(z), 1) if davidson_land_share(z) is not None else None)
    for z in PROP_ZIPS}

with open(os.path.join(HERE, "layer_density_results.json"), "w") as fh:
    json.dump(OUT, fh, indent=1, default=str)
print(json.dumps(OUT, indent=1, default=str))
