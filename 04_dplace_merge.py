#!/usr/bin/env python3
"""
Stage 4 — D-PLACE / Ethnographic Atlas Merge
Downloads EA072 (clubs and ceremonial associations) from D-PLACE.
Merges with criteria.json on society name / OWC code.
Outputs: data/processed/merged_dataset.csv + merged_dataset.json

D-PLACE EA072 values:
  1 = no clubs or associations
  2 = men's clubs or associations
  3 = women's clubs or associations  
  4 = clubs or associations for both sexes
  (higher values = more complex sodality structures in some codings)
"""

import json, csv, os, sys, urllib.request
from pathlib import Path
from datetime import datetime

BASE_DIR    = Path(__file__).parent.parent
CRITERIA_F  = BASE_DIR / "data/processed/criteria.json"
OUTPUT_JSON = BASE_DIR / "data/processed/merged_dataset.json"
OUTPUT_CSV  = BASE_DIR / "data/processed/merged_dataset.csv"
LOG_FILE    = BASE_DIR / "logs/stage4.log"

# D-PLACE API endpoint for EA072
DPLACE_URL = "https://d-place.org/api/v2/datapoints?parameters=EA072&format=json"
DPLACE_SOCIETIES_URL = "https://d-place.org/api/v2/societies?format=json"

CRITERIA_CODES = ["C01","C02","C03","C04","C05","C06","C07","C08","C09","C10","C11"]
CRITERIA_NAMES = {
    "C01":"transformation_symbolism","C02":"feasting","C03":"exotic_prestige_materials",
    "C04":"spatial_liminality","C05":"long_duration_institutional","C06":"burial_absence",
    "C07":"special_structure","C08":"remote_locations","C09":"ritual_paraphernalia_cache",
    "C10":"power_animal_iconography","C11":"interaction_sphere",
}

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def fetch_dplace(url):
    """Fetch D-PLACE API data."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "hayden-pipeline/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        log(f"  D-PLACE fetch error: {e}")
        return None

def encode_criterion(val):
    """Convert present/partial/absent/unclear to numeric."""
    return {"present": 2, "partial": 1, "absent": 0, "unclear": -1}.get(val, -1)

def main():
    log("="*60)
    log("Stage 4: D-PLACE / EA072 Merge")
    log("="*60)

    records = json.load(open(CRITERIA_F, encoding="utf-8"))
    log(f"Loaded {len(records)} extracted records")

    # Attempt D-PLACE download
    log("Fetching EA072 from D-PLACE...")
    dplace_data = fetch_dplace(DPLACE_URL)

    dplace_map = {}  # society_name_lower -> EA072 value
    if dplace_data:
        # Try to get society names too
        soc_data = fetch_dplace(DPLACE_SOCIETIES_URL)
        soc_lookup = {}
        if soc_data and "results" in soc_data:
            for s in soc_data["results"]:
                soc_lookup[s.get("id")] = s.get("pref_name","")

        if "results" in dplace_data:
            for dp in dplace_data["results"]:
                soc_id  = dp.get("society")
                soc_name = soc_lookup.get(soc_id,"").lower()
                value    = dp.get("coded_value")
                if soc_name:
                    dplace_map[soc_name] = value
            log(f"  D-PLACE: {len(dplace_map)} societies with EA072 coding")
    else:
        log("  D-PLACE unavailable — proceeding without merge (EA072 column will be null)")

    # Build flat records for CSV
    merged = []
    for rec in records:
        criteria = rec.get("criteria", {})
        soc_name_lower = rec.get("society_name","").lower()
        ethnic_lower   = rec.get("ethnic_group","").lower()

        # Try to match to D-PLACE
        ea072 = dplace_map.get(soc_name_lower) or dplace_map.get(ethnic_lower)

        flat = {
            "society_id":              rec.get("society_id"),
            "society_name":            rec.get("society_name"),
            "ethnic_group":            rec.get("ethnic_group"),
            "region":                  rec.get("region"),
            "chapter":                 rec.get("chapter"),
            "subsistence_type":        rec.get("subsistence_type"),
            "institution_type":        rec.get("institution_type"),
            "documentation_quality":   rec.get("documentation_quality"),
            "source_ethnographers":    rec.get("source_ethnographers"),
            "source_book":             rec.get("source_book"),
            "EA072_clubs_associations": ea072,
            "dplace_matched":          ea072 is not None,
            "notes":                   rec.get("notes",""),
        }

        # Add each criterion
        for code in CRITERIA_CODES:
            c   = criteria.get(code, {})
            val = c.get("value","unclear") if isinstance(c, dict) else "unclear"
            ev  = c.get("evidence","") if isinstance(c, dict) else ""
            name = CRITERIA_NAMES[code]
            flat[f"{code}_{name}"]          = val
            flat[f"{code}_{name}_numeric"]  = encode_criterion(val)
            flat[f"{code}_{name}_evidence"] = ev

        # Summary score: count of present/partial
        flat["criteria_met"] = sum(
            1 for code in CRITERIA_CODES
            if flat.get(f"{code}_{CRITERIA_NAMES[code]}") in ("present","partial")
        )
        merged.append(flat)

    # Save JSON
    json.dump(merged, open(OUTPUT_JSON,"w",encoding="utf-8"), indent=2, ensure_ascii=False)
    log(f"Saved JSON: {OUTPUT_JSON}")

    # Save CSV
    if merged:
        fields = list(merged[0].keys())
        with open(OUTPUT_CSV,"w",newline="",encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(merged)
        log(f"Saved CSV: {OUTPUT_CSV}")

    # Summary stats
    log(f"\nMerged dataset: {len(merged)} records")
    log(f"D-PLACE matched: {sum(1 for r in merged if r['dplace_matched'])}")

    for code in CRITERIA_CODES:
        col = f"{code}_{CRITERIA_NAMES[code]}"
        n_present = sum(1 for r in merged if r.get(col) in ("present","partial"))
        pct = 100 * n_present / len(merged) if merged else 0
        log(f"  {code}: {n_present}/{len(merged)} ({pct:.0f}%) present/partial")

if __name__ == "__main__":
    main()
