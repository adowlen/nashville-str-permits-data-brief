"""Analysis for the Nashville STR permits brief (Machine Readable).

Input: data/nashville_str_permits_2026-10-13.csv, the full Metro Nashville
Residential Short Term Rental Permits file pulled 2026-10-13 from the
ArcGIS Feature Service (see download.py). Output: stats.json, where every
figure carries its derivation in the key structure or a "method" note.

Definitions used throughout (also stated in the brief's methods section):
- "Current permits" = records with Permit_Status == "ISSUED". Verified at
  pull time: 100% of ISSUED records carry an expiration date after the
  pull date, so ISSUED is the live permit stock. All other statuses
  (EXPIRED, CANCELLED, REVOKED, DENIED-D, PENDING, etc.) are history.
- Permit class: the file records owner-occupied permits under code
  CAZ10A001 and not-owner-occupied permits under TWO codes, CAZ10A002
  (dominant 2015-2016, gone by 2024) and CAZ10A003 (dominant since).
  Both are labeled non/not owner occupied; they are two eras of the
  permitting system's coding, not two live categories, so this analysis
  merges them into "not owner occupied" and discloses the merge. The
  file cannot support a single-family vs multifamily split of the
  not-owner-occupied stock (no reliable field carries it).
- Owner key: Permit_Owner_Name normalized (uppercase, punctuation
  removed, whitespace collapsed, trailing legal suffixes LLC / INC /
  CORP / COMPANY / LTD / LP / LLP stripped). Name variants can still
  split one real-world owner into two keys; treat concentration as a
  floor, not an exact census of owners.
- Out-of-area tiers, computed only on rows with a usable owner mailing
  ZIP (first 5 digits) or state:
  * out-of-state: normalized Permit_Owner_State != "TN".
  * outside the county ZIP footprint: owner mailing ZIP (5-digit) is
    not among the property ZIP codes observed in this file. Every
    record is a Davidson County property (Metro Nashville-Davidson
    issues these permits), so the observed property-ZIP set is the
    county footprint as the permit file itself draws it. ZIP codes
    are postal geographies and a few straddle the county line; the
    tier is an approximation and is labeled as such.
  * same ZIP as the property: owner mailing ZIP == property ZIP.
"""
import json
import os
import re
from collections import Counter

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PULL_DATE = "2026-10-13"
PULL_TS = pd.Timestamp(PULL_DATE, tz="UTC")

df = pd.read_csv(os.path.join(HERE, "data", "nashville_str_permits_2026-10-13.csv"),
                 dtype=str, keep_default_na=False)
TOTAL = len(df)

# ---------- prep ----------
df["issued_dt"] = pd.to_datetime(pd.to_numeric(df["Date_Issued"], errors="coerce"), unit="ms", utc=True)
df["exp_dt"] = pd.to_datetime(pd.to_numeric(df["Expiration_Date"], errors="coerce"), unit="ms", utc=True)
df["issue_year"] = df["issued_dt"].dt.year

df["pclass"] = df["Permit_SubType"].map({
    "CAZ10A001": "owner_occupied",
    "CAZ10A002": "not_owner_occupied",
    "CAZ10A003": "not_owner_occupied",
}).fillna("unknown")

SUFFIXES = {"LLC", "INC", "CORP", "COMPANY", "LTD", "LP", "LLP", "CO"}
def owner_key(name):
    s = re.sub(r"[^A-Z0-9 ]", " ", str(name).upper())
    parts = [p for p in s.split() if p]
    while parts and parts[-1] in SUFFIXES:
        parts.pop()
    return " ".join(parts)

df["owner_key"] = df["Permit_Owner_Name"].map(owner_key)
df["owner_zip5"] = df["Permit_Owner_Zip"].str.strip().str[:5]
df["owner_zip5"] = df["owner_zip5"].where(df["owner_zip5"].str.fullmatch(r"\d{5}"), "")
df["owner_state_n"] = df["Permit_Owner_State"].str.strip().str.upper()
df["prop_zip"] = df["ZIP"].str.strip()
PROPERTY_ZIPS = sorted(set(z for z in df["prop_zip"] if re.fullmatch(r"\d{5}", z or "")))

def geo_tier(row):
    """Return dict of geography flags for a row, or None if unusable."""
    if not row["owner_zip5"] and not row["owner_state_n"]:
        return None
    out = {}
    out["out_of_state"] = bool(row["owner_state_n"] and row["owner_state_n"] != "TN")
    if row["owner_zip5"]:
        out["outside_county_footprint"] = row["owner_zip5"] not in PROPERTY_ZIPS
        out["same_zip_as_property"] = row["owner_zip5"] == row["prop_zip"]
    return out

df["geo"] = df.apply(geo_tier, axis=1)

def pct(n, d):
    return round(100.0 * n / d, 1) if d else None

def geo_block(frame, label):
    sub = frame[frame["geo"].notna()]
    with_zip = sub[sub["owner_zip5"] != ""]
    oos = with_zip["owner_state_n"].ne("") & with_zip["owner_state_n"].ne("TN")
    outside = with_zip["geo"].map(lambda g: g["outside_county_footprint"])
    buckets = {
        "base_rows_with_owner_zip": int(len(with_zip)),
        "out_of_state": int((oos).sum()),
        "in_tennessee_outside_county_footprint": int(((~oos) & outside).sum()),
        "inside_county_footprint": int(((~outside)).sum()),
        "note": "Mutually exclusive buckets on rows with a usable owner mailing ZIP. Out-of-state uses the owner state field; the footprint test uses the owner ZIP against the property ZIPs observed in the file.",
    }
    return {
        "zip_buckets": buckets,
        "scope": label,
        "rows": int(len(frame)),
        "rows_with_owner_geography": int(len(sub)),
        "share_out_of_state_pct": pct(int(sub["geo"].map(lambda g: g["out_of_state"]).sum()), len(sub)),
        "out_of_state_n": int(sub["geo"].map(lambda g: g["out_of_state"]).sum()),
        "rows_with_owner_zip": int(len(with_zip)),
        "share_outside_county_zip_footprint_pct": pct(int(with_zip["geo"].map(lambda g: g["outside_county_footprint"]).sum()), len(with_zip)),
        "outside_county_zip_footprint_n": int(with_zip["geo"].map(lambda g: g["outside_county_footprint"]).sum()),
        "share_same_zip_as_property_pct": pct(int(with_zip["geo"].map(lambda g: g["same_zip_as_property"]).sum()), len(with_zip)),
    }

def class_counts(frame):
    c = frame["pclass"].value_counts()
    return {k: int(c.get(k, 0)) for k in ["owner_occupied", "not_owner_occupied", "unknown"]}

def owner_concentration(frame, label):
    valid = frame[frame["owner_key"] != ""]
    counts = valid["owner_key"].value_counts()
    buckets = {
        "1 permit": int((counts == 1).sum()),
        "2-4 permits": int(((counts >= 2) & (counts <= 4)).sum()),
        "5-9 permits": int(((counts >= 5) & (counts <= 9)).sum()),
        "10-24 permits": int(((counts >= 10) & (counts <= 24)).sum()),
        "25+ permits": int((counts >= 25).sum()),
    }
    top = []
    for name, n in counts.head(10).items():
        rows = valid[valid["owner_key"] == name]
        top.append({
            "owner_key": name,
            "permits": int(n),
            "not_owner_occupied": int((rows["pclass"] == "not_owner_occupied").sum()),
            "owner_mailing_city": rows["Permit_Owner_City"].str.strip().str.upper().mode().iat[0] if len(rows) else "",
            "owner_mailing_state": rows["Permit_Owner_State"].str.strip().str.upper().mode().iat[0] if len(rows) else "",
        })
    ge10 = counts[counts >= 10]
    ge5 = counts[counts >= 5]
    return {
        "scope": label,
        "rows_with_owner_name": int(len(valid)),
        "unique_owners": int(counts.size),
        "owners_by_permit_count_bucket": buckets,
        "owners_with_10plus_permits": int(ge10.size),
        "permits_held_by_10plus_owners": int(ge10.sum()),
        "share_of_scope_permits_held_by_10plus_owners_pct": pct(int(ge10.sum()), len(valid)),
        "owners_with_5plus_permits": int(ge5.size),
        "permits_held_by_5plus_owners": int(ge5.sum()),
        "share_of_scope_permits_held_by_5plus_owners_pct": pct(int(ge5.sum()), len(valid)),
        "top_10_owners": top,
    }

stats = {}
stats["provenance"] = {
    "dataset": "Residential Short Term Rental Permits (Metro Nashville open data)",
    "source_service": "https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/Residential_Short_Term_Rental_Permits_view/FeatureServer/0",
    "hub_item_id": "b5315bda43ac459281dd35f04aa1be32",
    "pull_date": PULL_DATE,
    "rows_pulled": int(TOTAL),
    "fields": list(df.columns[:29]),
    "note": "Historical Socrata copy (data.nashville.gov dataset 2z82-v8pm) no longer resolves; the ArcGIS Feature Service above is the current publisher endpoint. Phone-number columns were dropped from the saved CSV (see download.py).",
}
stats["all_records"] = {
    "rows": int(TOTAL),
    "status_counts": {k: int(v) for k, v in df["Permit_Status"].value_counts().items()},
    "class_counts": class_counts(df),
    "unique_permit_numbers": int(df["Permit__"].nunique()),
    "unique_property_addresses_normalized": int(df["Address"].str.strip().str.upper().nunique()),
    "unique_parcels": int(df["Parcel"].str.strip().nunique()),
    "issue_year_counts": {str(int(k)): int(v) for k, v in df["issue_year"].dropna().value_counts().sort_index().items()},
    "date_issued_parse_rate_pct": pct(int(df["issued_dt"].notna().sum()), TOTAL),
}

issued = df[df["Permit_Status"] == "ISSUED"].copy()
stats["current_permits_issued"] = {
    "rows": int(len(issued)),
    "method": "Permit_Status == 'ISSUED'; verified 100% of these rows have Expiration_Date after the pull date.",
    "share_of_all_records_pct": pct(len(issued), TOTAL),
    "class_counts": class_counts(issued),
    "not_owner_occupied_share_pct": pct(int((issued["pclass"] == "not_owner_occupied").sum()), len(issued)),
    "unique_property_addresses_normalized": int(issued["Address"].str.strip().str.upper().nunique()),
    "unique_parcels": int(issued["Parcel"].str.strip().nunique()),
    "all_have_expiration_on_or_after_pull_date": bool((issued["exp_dt"] >= PULL_TS).all()),
    "expiring_on_pull_date_n": int((issued["exp_dt"] == PULL_TS).sum()),
    "subtype_code_counts_as_recorded": {k: int(v) for k, v in issued["Permit_Subtype_Description"].value_counts().items()},
}

# concentration by ZIP and council district among current permits
def top_table(frame, col, n=10):
    c = frame[col].value_counts().head(n)
    return [{"key": str(k), "permits": int(v), "share_pct": pct(int(v), len(frame))} for k, v in c.items()]

zip_all = issued["prop_zip"].value_counts()
stats["current_permits_issued"]["top_zips"] = top_table(issued, "prop_zip", 10)
stats["current_permits_issued"]["top5_zip_share_pct"] = pct(int(zip_all.head(5).sum()), len(issued))
stats["current_permits_issued"]["distinct_property_zips"] = int(issued["prop_zip"].nunique())
issued_cd = issued.copy()
issued_cd["cd_label"] = issued_cd["Council_Dist"].str.strip().str.replace(r"\.0$", "", regex=True)
stats["current_permits_issued"]["top_council_districts"] = top_table(issued_cd, "cd_label", 10)
stats["all_records"]["top_zips"] = top_table(df, "prop_zip", 10)

# geography / investor analysis
stats["geography"] = {
    "method": "See module docstring. Tiers computed per record on the owner mailing address fields (Permit_Owner_City/State/Zip), never on the property address.",
    "property_zip_footprint": PROPERTY_ZIPS,
    "all_records": geo_block(df, "all records"),
    "current_issued": geo_block(issued, "current permits (ISSUED)"),
    "current_issued_owner_occupied": geo_block(issued[issued["pclass"] == "owner_occupied"], "current, owner occupied"),
    "current_issued_not_owner_occupied": geo_block(issued[issued["pclass"] == "not_owner_occupied"], "current, not owner occupied"),
    "current_issued_top_out_of_state_owner_states": [
        {"state": k, "permits": int(v)} for k, v in
        issued[issued["owner_state_n"].ne("") & issued["owner_state_n"].ne("TN")]["owner_state_n"].value_counts().head(8).items()
    ],
    "current_issued_top_owner_mailing_cities_outside_footprint": [
        {"city_state": f"{c}, {s}", "permits": int(v)} for (c, s), v in
        Counter(zip(
            issued.loc[issued["geo"].map(lambda g: bool(g) and g.get("outside_county_footprint", False)), "Permit_Owner_City"].str.strip().str.upper(),
            issued.loc[issued["geo"].map(lambda g: bool(g) and g.get("outside_county_footprint", False)), "owner_state_n"],
        )).most_common(8)
    ],
}

stats["owner_concentration"] = {
    "method": "Owner key = normalized Permit_Owner_Name (see docstring). Concentration is a floor: spelling variants of one owner can survive normalization as separate keys.",
    "all_records": owner_concentration(df, "all records"),
    "current_issued": owner_concentration(issued, "current permits (ISSUED)"),
}

# portfolio shape: are big holders scattered portfolios or single buildings?
def addr_norm(s):
    return s.str.strip().str.upper().str.replace(r"\s+", " ", regex=True)

issued_addr = issued.assign(addr_n=addr_norm(issued["Address"]))
addr_counts = issued_addr["addr_n"].value_counts()
parcel_counts = issued["Parcel"].str.strip().value_counts()
top_owner_spread = []
for o in stats["owner_concentration"]["current_issued"]["top_10_owners"][:5]:
    rows = issued_addr[issued_addr["owner_key"] == o["owner_key"]]
    top_owner_spread.append({
        "owner_key": o["owner_key"],
        "permits": o["permits"],
        "unique_property_addresses": int(rows["addr_n"].nunique()),
        "top_address": str(rows["addr_n"].mode().iat[0]) if len(rows) else "",
        "top_address_permits": int(rows["addr_n"].value_counts().iat[0]) if len(rows) else 0,
    })
stats["portfolio_shape_current_issued"] = {
    "method": "Grouped by normalized property Address and by Parcel among ISSUED records.",
    "addresses_with_10plus_permits": int((addr_counts >= 10).sum()),
    "permits_at_addresses_with_10plus": int(addr_counts[addr_counts >= 10].sum()),
    "share_permits_at_addresses_with_10plus_pct": pct(int(addr_counts[addr_counts >= 10].sum()), len(issued)),
    "parcels_with_10plus_permits": int((parcel_counts >= 10).sum()),
    "permits_at_parcels_with_10plus": int(parcel_counts[parcel_counts >= 10].sum()),
    "share_permits_at_parcels_with_10plus_pct": pct(int(parcel_counts[parcel_counts >= 10].sum()), len(issued)),
    "largest_single_address": {"address": str(addr_counts.index[0]), "permits": int(addr_counts.iat[0])},
    "top_5_owner_address_spread": top_owner_spread,
}

# issuance trend by class (all records, by Date_Issued year)
trend = {}
for yr, g in df.dropna(subset=["issue_year"]).groupby("issue_year"):
    cc = class_counts(g)
    trend[str(int(yr))] = {"total": int(len(g)), **cc}
stats["issue_year_by_class"] = trend

stats["data_quality"] = {
    "owner_name_blank_rows": int((df["Permit_Owner_Name"].str.strip() == "").sum()),
    "owner_zip_blank_or_unusable_rows": int((df["owner_zip5"] == "").sum()),
    "owner_state_blank_rows": int((df["owner_state_n"] == "").sum()),
    "property_zip_blank_rows": int((df["prop_zip"].str.strip() == "").sum()),
    "council_district_blank_rows": int((df["Council_Dist"].str.strip() == "").sum()),
    "duplicate_permit_number_rows": int(TOTAL - df["Permit__"].nunique()),
    "subtype_code_history": "CAZ10A002 (not owner occupied, legacy label) issued counts by year collapse after 2016 and reach zero by 2024 while CAZ10A003 grows; the two codes are treated as one not-owner-occupied class across eras.",
}

with open(os.path.join(HERE, "stats.json"), "w") as fh:
    json.dump(stats, fh, indent=2)
print("wrote stats.json")
print(json.dumps({
    "total": TOTAL,
    "issued": int(len(issued)),
    "issued_noo_share": stats["current_permits_issued"]["not_owner_occupied_share_pct"],
    "geo_issued_noo": stats["geography"]["current_issued_not_owner_occupied"],
    "geo_issued": stats["geography"]["current_issued"],
    "conc_issued": {k: v for k, v in stats["owner_concentration"]["current_issued"].items() if k != "top_10_owners"},
    "top5_zip_share": stats["current_permits_issued"]["top5_zip_share_pct"],
}, indent=1))
