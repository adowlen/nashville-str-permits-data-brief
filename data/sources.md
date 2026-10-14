# Source audit: Nashville STR permits brief (2026-10-14)

Every figure in brief-draft.md, traced to its derivation. Unless noted,
the source is the single dataset below, pulled in full on 2026-10-13.
All counts were produced by analyze.py and are stored in stats.json.

## The dataset

- Name: Residential Short Term Rental Permits (Metro Nashville open data)
- Current endpoint (used): ArcGIS Feature Service
  https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/Residential_Short_Term_Rental_Permits_view/FeatureServer/0
  (ArcGIS Hub item b5315bda43ac459281dd35f04aa1be32, owner NashvilleOpenData)
- Pull: 2026-10-13, paginated query ordered by ObjectId, 17,612 records,
  server count confirmed with returnCountOnly before download
- Not used: the historical Socrata dataset (data.nashville.gov, id
  2z82-v8pm). Its API returns 404 as of the pull date; the portal now
  serves this file through ArcGIS.
- Saved copy: data/nashville_str_permits_2026-10-13.csv (29 of 37 fields;
  the 8 applicant/contact phone columns were dropped at download time
  and never used; see download.py)
- Fields relied on: Permit_Status, Permit_SubType,
  Permit_Subtype_Description, Date_Issued, Expiration_Date, ZIP,
  Council_Dist, Parcel, Address, Permit_Owner_Name, Permit_Owner_City,
  Permit_Owner_State, Permit_Owner_Zip

## Figure-by-figure audit

1. **17,612 records in the file**
   Server count (returnCountOnly) = 17,612; downloaded rows = 17,612.

2. **7,017 current permits**
   Filter: Permit_Status == "ISSUED". Verification: every one of
   these records has an Expiration_Date on or after the pull date
   2026-10-13 (epoch-ms field, parsed as UTC); 3 expire on the pull
   date itself and none before it. stats.json:
   current_permits_issued.rows and
   all_have_expiration_on_or_after_pull_date.

3. **Status counts (EXPIRED 8,024; CANCELLED 2,266; REVOKED 164;
   DENIED-D 38; PENDING 37; tail 66)**
   Permit_Status value counts over all records. Tail = EXPIREEXT 42 +
   HOLD 18 + REFUNDED 3 + VOID 2 + OK TO PAY 1 = 66.

4. **71.4% of current permits not owner occupied (5,011 of 7,017);
   owner occupied 2,006 (28.6%)**
   Permit class from Permit_SubType: CAZ10A001 = owner occupied;
   CAZ10A002 + CAZ10A003 = not owner occupied (merged; see item 12),
   restricted to ISSUED records. As recorded, the ISSUED subtype labels
   are: "Not Owner Occupied" 4,676 (CAZ10A003), "Non-Owner Occupied" 335
   (CAZ10A002), "Owner Occupied" 2,006 (CAZ10A001). Labels are
   paraphrased here with plain hyphens.

5. **First issuances by year; peaks 2018 (2,181) and 2022 (2,106)**
   Date_Issued (epoch ms) is parseable on 16,084 of 17,612 records
   (91.3%); 1,528 records carry no usable issue date and are excluded
   from the trend only. Earliest issue date 2015-04-06; latest
   2026-10-08; yearly counts sum to 16,084. Chart:
   charts/issuance_trend.png; stats.json: issue_year_by_class.

6. **49.9% of current investor permits mail from outside the county
   footprint (derived)**
   Scope: ISSUED + not owner occupied, owner mailing ZIP usable
   (5-digit): base 4,996. Numerator: mailing ZIP not in the set of
   property ZIP codes observed in the file (34 ZIPs, listed in
   stats.json geography.property_zip_footprint): 2,493. 2,493 / 4,996
   = 49.9%. Method label: derived.

7. **40.4% of current investor permits mail from out of state (derived)**
   Scope: ISSUED + not owner occupied, owner geography present (state
   or ZIP): base 4,999. Numerator: normalized Permit_Owner_State
   is not "TN": 2,018. 2,018 / 4,999 = 40.4%.
   Reconciliation with the chart buckets: on the ZIP-usable base
   (4,996), the out-of-state bucket is 2,016 records (40.4% at one
   decimal). The 2-record difference is records with a state but no
   usable ZIP. Chart: charts/owner_geography.png uses the ZIP base and
   the mutually exclusive buckets inside footprint 2,503 (50.1%),
   Tennessee outside footprint 477 (9.5%), out of state 2,016 (40.4%).

8. **Control: owner-occupied permits 98.5% inside footprint, 0.8%
   out of state, 95.3% same ZIP as the property (derived)**
   Same derivations on ISSUED + owner occupied: ZIP base 2,000,
   inside footprint 1,971 (98.55%, reported in the brief as 98.5%);
   state base 2,000, out of state 15 (0.8%); owner ZIP equal to
   property ZIP 1,907 of 2,000 (95.35%, reported as 95.3%).
   Investor comparison figure: same-ZIP share for not owner occupied
   is 711 of 4,996 (14.2%). Verification note: 98.55% and 95.35% sit
   exactly on a one-decimal rounding boundary; the brief's figures
   follow the analysis script's float rounding.

9. **Out-of-state sources: California 578, Florida 400 (current
   permits, all classes)**
   Permit_Owner_State value counts over ISSUED records with a non-TN
   state. Next: Texas 142, New York 141. Mailing cities outside the
   footprint: Miami FL 330, San Francisco CA 287, New York NY 94,
   Franklin TN 79, Murfreesboro TN 76.

10. **4,696 distinct current owners; 90.5% hold one permit; 47 owners
    hold 10+, totaling 1,569 permits (22.4%); 96 owners hold 5+,
    totaling 1,900 (27.1%) (derived)**
    Group ISSUED records by normalized owner name (uppercase,
    punctuation removed, whitespace collapsed, trailing legal suffixes
    LLC/INC/CORP/COMPANY/LTD/LP/LLP stripped). 13 of 17,612 records
    (all records) have a blank owner name; among ISSUED records all
    carry a name. Buckets: 1 permit 4,250 owners; 2-4: 350; 5-9: 49;
    10-24: 34; 25+: 13. stats.json: owner_concentration.current_issued.

11. **Top holders: Bop Nest Nashville 328 (Miami, FL); Sixth South
    Partners 289 (San Francisco, CA); combined 617 = 8.8% of current
    permits and 12.3% of current investor permits**
    Same grouping as item 10. Owner names as recorded (normalization
    only). Mailing city/state are the modal values across each owner's
    records. Both holders' records are 100% not owner occupied.
    Address spread: distinct normalized Address strings per owner:
    Bop Nest Nashville 326, Sixth South Partners 289 (address strings
    include unit numbers). stats.json:
    portfolio_shape_current_issued.top_5_owner_address_spread.

12. **Two not-owner-occupied codes merged**
    CAZ10A002 issued counts by Date_Issued year: 587 (2015), 514
    (2016), 256 (2017), 109 (2018), 73 (2019), 11 (2020), 7 (2021),
    6 (2022), 1 (2023), 0 (2024), 1 (2025), 0 (2026). CAZ10A003 grows
    across the same years. Purpose free text contains no reliable
    single-family vs multifamily marker (the strings "multifamily"
    and "multi-family" appear in 0.0% to 0.5% of Purpose values in
    every subtype), so no house-versus-condo split is claimed from
    the subtype field.

13. **ZIP concentration: 37203 holds 1,710 current permits (24.4%);
    top five ZIPs hold 62.2%**
    ZIP value counts over ISSUED records. Top five: 37203 (1,710),
    37207 (809), 37208 (721), 37206 (665), 37212 (461); sum 4,366;
    4,366 / 7,017 = 62.2%. Chart: charts/top_zips_current.png.

14. **Council district concentration: District 19 holds 1,889 (26.9%);
    top four districts hold 62.9%**
    Council_Dist value counts over ISSUED records (7 records in the
    full file have a blank district). Top four: 19 (1,889), 17 (960),
    5 (802), 21 (763); sum 4,414; 4,414 / 7,017 = 62.9%.

15. **Parcel layer: 34 parcels hold 10+ current permits, totaling
    1,319 (18.8%); current permits sit on 5,472 distinct parcels and
    6,976 distinct normalized addresses**
    Group ISSUED records by Parcel and by normalized Address. Largest
    single address string: 321 McMillin St, 15 permits.

16. **All-records context: unique property addresses 14,343; unique
    parcels 10,730; duplicate permit numbers 30**
    Address normalized (trim, uppercase). Permit__ distinct count
    17,582 against 17,612 rows.

## Verification-pass additions (2026-10-13, independent recheck)

The figures below were produced by the independent verification pass
(verification.md, verify_core.py, verify_details.py, layer scripts),
not by analyze.py. Layered sources used:

- Davidson County assessor parcels: Metro Nashville open data,
  Parcels view (ArcGIS Feature Service, same org as the permit file),
  fields STANPAR and LUDesc, queried 2026-10-13.
- U.S. Census Bureau, ACS 2024 5-year estimates, table B25001
  (total housing units), ZCTA level, from the official table-based
  summary file acsdt5y2024-b25001.dat (the Census API itself now
  requires a key; keyless queries redirect to a missing-key page).
- U.S. Census Bureau, 2020 Census ZCTA-to-county relationship file
  (tab20_zcta520_county20_natl.txt), land-area allocation to
  Davidson County (FIPS 47037).

17. **Property type of current permits (derived, assessor join)**
    Join: permit Parcel = assessor STANPAR. 5,464 of 5,472 distinct
    current parcels matched (99.85%); 7,000 of 7,017 current permits
    carry a matched parcel (99.76%). No STANPAR returned conflicting
    land-use descriptions. Investor class (matched n = 4,998):
    condo 2,547 (51.0%); apartment or multifamily 1,367 (27.4%);
    single-family 260 (5.2%); remainder as recorded (vacant
    residential land 236, no land-use description 268, commercial
    and miscellaneous uses the balance). All current (n = 7,000):
    condo 2,837 (40.5%), single-family 1,792 (25.6%), apartment or
    multifamily 1,499 (21.4%). Owner occupied (n = 2,002):
    single-family 1,532 (76.5%). Top holders: Bop Nest Nashville
    328 of 328 matched permits on APARTMENT: HIGH RISE parcels;
    Sixth South Partners 289 of 289, same description. Buckets:
    condo = LUDesc containing CONDO; single-family = containing
    SINGLE FAM; apartment or multifamily = containing APARTMENT,
    APT, DUPLEX, TRIPLEX, QUADPLEX, or MULTI.

18. **Density: current permits per 1,000 housing units by ZIP
    (derived, ACS layer)**
    Numerator: current permits by property ZIP (item 13). Denominator:
    ACS 2024 5-year B25001 total housing units for the matching ZCTA.
    7,016 of 7,017 current permits sit on ZCTAs with an ACS value
    (ZIP 37213 has none and is excluded); those ZCTAs hold 418,152
    housing units, for a citywide rate of 16.8 per 1,000. Top rates:
    37201: 346 / 1,309 = 264.3; 37203: 1,710 / 18,304 = 93.4;
    37208: 721 / 11,360 = 63.5; 37212: 461 / 8,288 = 55.6;
    37206: 665 / 14,065 = 47.3; 37207: 809 / 19,727 = 41.0.
    Caveat: ZCTAs approximate postal ZIPs; ZCTA 37201 is a small,
    mostly commercial downtown geography, which is exactly why its
    per-unit rate is extreme. Chart: charts/density_by_zip.png.

19. **Footprint sensitivity (derived, Census relationship file)**
    Brief method (item 6): outside share for current investor
    permits = 2,493 of 4,996 = 49.9%. Census land-area variants:
    counting a mailing ZCTA as outside when it contains no Davidson
    County land gives 2,490 of 4,996 (49.8%); counting it as outside
    unless a majority of its land area lies in Davidson County
    gives 2,850 of 4,996 (57.0%). The file footprint therefore
    understates, not overstates, the outside share under a majority
    rule, because footprint ZIPs 37064 (0.8% Davidson land), 37122
    (0.9%), 37027 (13.6%), 37135 (8.2%), and 37015 (5.8%) are mostly
    outside the county. Control under the majority rule: owner
    occupied outside = 39 of 2,000 (2.0%).

20. **Policy timeline and trend decomposition (derived + named
    sources)**
    Milestones: Ordinance BL2014-951 created the permit system,
    capped non-owner-occupied permits at 3% of single-family and
    two-family units per census tract, and set applications to open
    March 31, 2015 with enforcement from July 1, 2015 (ordinance
    text, Metro legisarchive, legisarchive.nashville.gov). In
    January 2018 the Metro Council passed BL2017-608, barring new
    non-owner-occupied permits in residential zones and phasing out
    existing ones over three years (Associated Press reporting,
    January 2018). In April 2018 Tennessee's Short-Term Rental Unit
    Act (Tenn. Code Ann. 13-7-601 et seq.) was signed, grandfathering
    existing permits and voiding the phase-out (Associated Press,
    April 24, 2018). Decomposition from the file's Date_Issued
    months: December 2017 investor issuance = 200 (2017 monthly
    high; next-highest month 113), of which 505 Apartments = 125;
    January 2018 investor issuance = 56. Bop Nest Nashville permits
    issued Nov-Dec 2018 = 327; 2018 total without them = 1,854,
    below 2019 (1,993). Sixth South Partners permits issued in 2022
    = 297; 2022 total without them = 1,809, also below 2019.

21. **Count integrity inside the current stock (verification)**
    10 permit numbers appear twice within the ISSUED set; every pair
    shares address, parcel, owner, and class (apparent duplicate
    records of one permit). Deduplicated recount: stock 7,007;
    investor share 5,005 of 7,007 (71.4%); investor out-of-state
    40.3% and outside-footprint 49.8% on the deduplicated bases.
    No headline figure moves by more than 0.1 percentage points.
    Separately, all 42 EXPIREEXT records carry expiration dates on
    or after the pull date (window 2026-10-13 to 2026-11-08); the
    brief treats them as history. Counting them as live: stock
    7,059, investor share 71.3%.
