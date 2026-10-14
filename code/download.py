"""Download the full Nashville Residential Short Term Rental Permits dataset.

Source (current, verified 2026-10-13): Metro Nashville open data, ArcGIS
Feature Service "Residential_Short_Term_Rental_Permits_view" (item
b5315bda43ac459281dd35f04aa1be32), layer 0.

Note: the historical Socrata dataset on data.nashville.gov
(Residential Short Term Rental Permits, id 2z82-v8pm) no longer resolves
(portal API returns 404). Nashville's open data portal now serves this
dataset through ArcGIS. This script paginates the FeatureServer query
endpoint (maxRecordCount 1000) ordered by ObjectId.

The six applicant/contact phone-number columns are dropped from the
saved CSV: they carry no analytic value and are personal contact data.
All other fields are saved verbatim.
"""
import csv
import json
import os
import urllib.parse
import urllib.request

SVC = ("https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/"
       "Residential_Short_Term_Rental_Permits_view/FeatureServer/0")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)

DROP = {
    "Applicant_Home_Phone", "Applicant_Mobile_Phone", "Applicant_Work_Phone",
    "Applicant_Work_Phone_Ext", "Contact_Home_Phone", "Contact_Mobile_Phone",
    "Contact_Work_Phone", "Contact_Work_Phone_Ext",
}
PAGE = 1000


def fetch(params):
    url = SVC + "/query?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def main():
    total = fetch({"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
    print("server count:", total)
    rows = []
    offset = 0
    while True:
        page = fetch({
            "where": "1=1",
            "outFields": "*",
            "orderByFields": "ObjectId ASC",
            "resultOffset": offset,
            "resultRecordCount": PAGE,
            "f": "json",
        })
        feats = page.get("features", [])
        if not feats:
            break
        for f in feats:
            rows.append(f["attributes"])
        print(f"  offset {offset}: cumulative {len(rows)}")
        if len(feats) < PAGE:
            break
        offset += PAGE

    fields = [k for k in rows[0].keys() if k not in DROP]
    path = os.path.join(OUT, "nashville_str_permits_2026-10-13.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fields})
    print("saved", path, "rows:", len(rows), "cols:", len(fields))


if __name__ == "__main__":
    main()
