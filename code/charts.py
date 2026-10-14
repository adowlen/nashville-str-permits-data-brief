"""Charts for the Nashville STR permits brief - Machine Readable brand palette.

Every figure is drawn from stats.json (produced by analyze.py) and carries
its scope and source on the graphic. Text uses plain hyphens only.
"""
import json
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

CHARCOAL = "#23221F"
PAPER = "#F1E7DA"
AMBER = "#E8A33D"
TEAL = "#2AA198"
AMBER_DIM = "#8A6420"
TEAL_DIM = "#1E6E68"
GRID = "#4A453C"
TEXT = "#F1E7DA"
TEXT_DIM = "#B8AE9C"

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "charts")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": CHARCOAL,
    "axes.facecolor": CHARCOAL,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT,
    "text.color": TEXT,
    "xtick.color": TEXT_DIM,
    "ytick.color": TEXT_DIM,
    "grid.color": GRID,
    "grid.alpha": 0.5,
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.titlecolor": TEXT,
})

s = json.load(open(os.path.join(HERE, "stats.json")))
SRC = "Source: Metro Nashville Residential Short Term Rental Permits file (open data), pulled Oct 13, 2026."


def save(fig, name, rect_bottom=0.0):
    fig.tight_layout(rect=[0, rect_bottom, 1, 1])
    fig.savefig(os.path.join(OUT, name), dpi=150, facecolor=CHARCOAL)
    plt.close(fig)
    print("saved", name)


def footnote(fig, text):
    fig.text(0.012, 0.014, text, fontsize=8.5, color=TEXT_DIM, va="bottom")


# 1. Concentration: top 10 ZIPs among current (ISSUED) permits
zips = s["current_permits_issued"]["top_zips"][::-1]
fig, ax = plt.subplots(figsize=(10, 6))
ax.barh([z["key"] for z in zips], [z["permits"] for z in zips], color=AMBER, edgecolor="none")
ax.set_title("Where Nashville's current STR permits sit: top 10 ZIP codes")
ax.set_xlabel("current permits (permit status ISSUED)")
ax.set_xlim(0, 2050)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
for i, z in enumerate(zips):
    ax.text(z["permits"] * 1.01, i, f"{z['permits']:,}  ({z['share_pct']}%)", va="center", fontsize=9, color=TEXT)
footnote(fig, "Scope: 7,017 current permits. Top 5 ZIPs hold 62.2% of all current permits.\n" + SRC)
save(fig, "top_zips_current.png", rect_bottom=0.07)

# 2. Owner geography: the investor split, with owner-occupied as the control
geo = s["geography"]
def bucket_pct(block):
    b = block["zip_buckets"]
    n = b["base_rows_with_owner_zip"]
    return [100 * b["inside_county_footprint"] / n,
            100 * b["in_tennessee_outside_county_footprint"] / n,
            100 * b["out_of_state"] / n]

oo_pcts = bucket_pct(geo["current_issued_owner_occupied"])
noo_pcts = bucket_pct(geo["current_issued_not_owner_occupied"])
classes = [
    ("Owner occupied\n(2,006 current permits)", oo_pcts),
    ("Not owner occupied\n(5,011 current permits)", noo_pcts),
]
labels = ["Owner mails from inside Davidson County", "Owner mails from elsewhere in Tennessee", "Owner mails from out of state"]
colors = [TEAL, AMBER_DIM, AMBER]
fig, ax = plt.subplots(figsize=(10, 5.6))
for yi, (name, pcts) in enumerate(classes):
    left = 0.0
    for seg, c in zip(pcts, colors):
        ax.barh(yi, seg, left=left, color=c, edgecolor="none")
        if seg >= 4:
            ax.text(left + seg / 2, yi, f"{seg:.1f}%", ha="center", va="center", fontsize=10,
                    color=CHARCOAL if c == AMBER else TEXT, fontweight="bold")
        left += seg
ax.set_yticks([0, 1])
ax.set_yticklabels([c[0] for c in classes], fontsize=10.5)
ax.set_xlim(0, 100)
ax.set_xlabel("share of current permits, by owner mailing address (derived)")
ax.set_title("Half of Nashville's investor STR permits are owned from outside the county")
ax.legend(labels, frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1)
footnote(fig, f"Method (derived): owner mailing ZIP tested against the property ZIP codes in the permit file;\nout-of-state uses the owner state field. Owner-occupied permits are the control: {oo_pcts[0]:.1f}% mail\nfrom inside the county footprint. " + SRC)
save(fig, "owner_geography.png", rect_bottom=0.15)

# 3. Issuance trend by class, 2015-2026 (file starts April 2015; 2026 is year to date)
trend = s["issue_year_by_class"]
years = sorted(trend.keys())
oo = [trend[y]["owner_occupied"] for y in years]
noo = [trend[y]["not_owner_occupied"] for y in years]
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.bar(years, noo, color=AMBER, edgecolor="none", label="Not owner occupied")
ax.bar(years, oo, bottom=noo, color=TEAL, edgecolor="none", label="Owner occupied")
ax.set_title("STR permits first issued per year, by permit class")
ax.set_ylabel("permits first issued")
ax.legend(frameon=False, fontsize=10)
for i, y in enumerate(years):
    ax.text(i, noo[i] + oo[i] + 60, f"{noo[i] + oo[i]:,}", ha="center", fontsize=8.5, color=TEXT)
ax.annotate("Dec 2017: investor issuance hits a year-high 200,\nweeks before the Jan 2018 phase-out vote",
            xy=(2, trend["2017"]["owner_occupied"] + trend["2017"]["not_owner_occupied"]),
            xytext=(-0.4, 2880), fontsize=8.5, color=TEXT,
            arrowprops=dict(arrowstyle="-", color=TEXT_DIM, lw=0.8))
ax.annotate("2018 peak is one portfolio:\nBop Nest Nashville, 327 permits\nin Nov-Dec 2018",
            xy=(3, trend["2018"]["owner_occupied"] + trend["2018"]["not_owner_occupied"]),
            xytext=(4.5, 2720), fontsize=8.5, color=TEXT,
            arrowprops=dict(arrowstyle="-", color=TEXT_DIM, lw=0.8))
ax.annotate("2022 peak is one portfolio:\nSixth South Partners, 297 permits",
            xy=(7, trend["2022"]["owner_occupied"] + trend["2022"]["not_owner_occupied"]),
            xytext=(7.4, 2450), fontsize=8.5, color=TEXT,
            arrowprops=dict(arrowstyle="-", color=TEXT_DIM, lw=0.8))
ax.set_ylim(0, 3050)
ax.text(0, -620, "Scope: all 17,612 records in the file, by Date Issued. The file opens April 2015; 2026 runs through Oct 8.\nPermits last one year, so most records shown here have since expired or been renewed under a new record.\n" + SRC,
        fontsize=8.5, color=TEXT_DIM, transform=ax.transData)
save(fig, "issuance_trend.png")

# 4. Top owners among current permits
def pretty(name):
    t = name.title()
    t = t.replace("Llc", "LLC").replace(" Et Al", " et al")
    t = re.sub(r"\b(\d+)(St|Nd|Rd|Th)\b", lambda m: m.group(1) + m.group(2).lower(), t)
    return t

top = s["owner_concentration"]["current_issued"]["top_10_owners"][::-1]
names = [pretty(o["owner_key"]) for o in top]
vals = [o["permits"] for o in top]
cols = [AMBER if o["owner_mailing_state"] not in ("TN", "") else TEAL for o in top]
fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(names, vals, color=cols, edgecolor="none")
ax.set_title("The largest current permit holders in Nashville")
ax.set_xlabel("current permits held (permit status ISSUED)")
ax.set_xlim(0, 460)
for i, o in enumerate(top):
    loc = f"{o['owner_mailing_city'].title()}, {o['owner_mailing_state']}" if o["owner_mailing_state"] else "mailing address on file"
    ax.text(o["permits"] * 1.02, i, f"{o['permits']}  -  mails from {loc}", va="center", fontsize=9, color=TEXT)
footnote(fig, "Owner names as recorded on the permit, normalized (derived; see brief methods). Amber = owner mailing\naddress out of state, teal = Tennessee. 47 owners hold 10 or more permits: 22.4% of the current stock.\n" + SRC)
save(fig, "top_owners_current.png", rect_bottom=0.09)

# 5. Hero graphic: the killer number
fig, ax = plt.subplots(figsize=(12, 6.75))
ax.axis("off")
ax.text(0.5, 0.86, "MACHINE READABLE", ha="center", fontsize=15, color=TEAL, fontweight="bold")
ax.text(0.5, 0.60, "49.9%", ha="center", fontsize=110, color=AMBER, fontweight="bold")
ax.text(0.5, 0.375, "of Nashville's current investor short-term rental permits\nare owned from outside Davidson County",
        ha="center", fontsize=19, color=TEXT, linespacing=1.5)
ax.text(0.5, 0.20, "7,017 current permits  -  71.4% not owner occupied  -  40.4% of investor permits mail from out of state",
        ha="center", fontsize=13.5, color=TEXT_DIM)
ax.text(0.5, 0.075, SRC, ha="center", fontsize=10, color=TEXT_DIM)
save(fig, "hero.png")

# 6. Density: current permits per 1,000 housing units, top 8 ZIPs (verification layer)
dens = [d for d in s["verification_extensions"]["density_layer"]["by_property_zip"]
        if d["permits_per_1000_hu"] is not None]
dens = sorted(dens, key=lambda d: d["permits_per_1000_hu"], reverse=True)[:8][::-1]
fig, ax = plt.subplots(figsize=(10, 5.6))
ax.barh([d["zip"] for d in dens], [d["permits_per_1000_hu"] for d in dens], color=TEAL, edgecolor="none")
ax.set_title("Per home, the densest STR footprint is the downtown core")
ax.set_xlabel("current STR permits per 1,000 housing units (derived)")
for i, d in enumerate(dens):
    ax.text(d["permits_per_1000_hu"] * 1.02, i,
            f"{d['permits_per_1000_hu']}  ({d['current_permits']:,} permits, {d['acs2024_housing_units']:,} housing units)",
            va="center", fontsize=9, color=TEXT)
ax.set_xlim(0, 400)
footnote(fig, "Derived: current permits (permit file) over total housing units, Census Bureau ACS 2024 5-year,\ntable B25001, ZCTA level (ZCTAs approximate postal ZIPs). ZIP 37213 excluded: no ACS housing units.\n" + SRC)
save(fig, "density_by_zip.png", rect_bottom=0.09)

print("done")
