#!/usr/bin/env python3
"""
Download Census national_county.txt and write data/county_list.json.

Each entry: { "id": "01001", "label": "Alabama - Autauga County" }
id is 5-digit state FIPS + county FIPS (2 + 3).
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from urllib.request import urlopen

URL = "https://www2.census.gov/geo/docs/reference/codes/files/national_county.txt"
OUT = Path(__file__).resolve().parents[1] / "data" / "county_list.json"

STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "AS": "American Samoa",
    "GU": "Guam",
    "MP": "Northern Mariana Islands",
    "PR": "Puerto Rico",
    "VI": "U.S. Virgin Islands",
    "UM": "U.S. Minor Outlying Islands",
}


def main() -> None:
    with urlopen(URL, timeout=60) as resp:
        text = resp.read().decode("utf-8", errors="replace")

    rows: list[dict[str, str]] = []
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if len(row) < 4:
            continue
        stusps, stfp, cofp, cname = row[0], row[1], row[2], row[3]
        stfp = stfp.strip().zfill(2)
        cofp = cofp.strip().zfill(3)
        cid = f"{stfp}{cofp}"
        state_name = STATE_NAMES.get(stusps.strip(), stusps.strip())
        label = f"{state_name} - {cname.strip()}"
        rows.append({"id": cid, "label": label})

    rows.sort(key=lambda r: r["label"].lower())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "source": URL, "counties": rows}
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} counties to {OUT}")


if __name__ == "__main__":
    main()
