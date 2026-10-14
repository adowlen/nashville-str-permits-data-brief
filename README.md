# Half of Nashville's Investor STR Permits Are Owned From Outside the County

A data brief on Nashville's short-term rental permits: all 17,612 permit records Metro Nashville has published since 2015 (pulled October 13, 2026), who owns the legal STR market, and where it actually sits.

**Headline:** Nashville has 7,017 STR permits in force. 71.4% are not owner occupied, 49.9% of the investor permits are owned from outside Davidson County, and 40.4% mail from another state. Only 5.2% of investor permits sit on single-family parcels - the investor STR market is a buildings market, not a houses market.

![Hero](charts/hero.png)

Read the full brief: [brief/nashville-str-permits-brief.md](brief/nashville-str-permits-brief.md)

## Contents

- `brief/` - the narrative brief with findings, charts, methods, and caveats
- `charts/` - hero graphic + 5 charts (PNG)
- `data/` - aggregated statistics (`stats.json`) and the per-figure source audit (`sources.md`)
- `code/` - download, analysis, chart, and layering scripts (`download.py`, `analyze.py`, `charts.py`, `layer_density.py`, `layer_property_type.py`)

## Data sources

All public:

- Metro Nashville Residential Short Term Rental Permits file (open data, ArcGIS Feature Service), 17,612 records, pulled October 13, 2026
- Davidson County assessor parcel file (land use join for the property-type finding)
- US Census Bureau, ACS 2024 5-year estimates, housing units by ZCTA (density finding)
- Metro Nashville ordinance BL2014-951; BL2017-608 and the April 2018 Tennessee Short-Term Rental Unit Act (policy timeline, via AP reporting and the Anderson v. Metro opinion)

## Reproduce

1. Run `python code/download.py` - pulls the full permit file from Metro's ArcGIS service into `data/`
2. Run `python code/analyze.py` - writes `stats.json`
3. Run `python code/charts.py` - charts land in `charts/`
4. Optional layers: `python code/layer_property_type.py` (assessor join), `python code/layer_density.py` (ACS density)

Requires Python 3 with matplotlib and pandas.

## Caveats (short version)

Permits counted, not listings: the file cannot see unpermitted rentals. Owner geography is derived from owner mailing addresses, a paperwork signal, not proof of residence - the same test run on owner-occupied permits returns 98.5% local, which is the control. "Currently in force" means permit status ISSUED in Metro's file; 10 permit numbers appear twice with identical details (deduped stock 7,007; no share moves more than 0.1 points). Assessor land use is today's classification and can post-date a permit. Full methods and caveats in the brief.
