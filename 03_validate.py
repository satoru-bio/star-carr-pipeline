#!/usr/bin/env python3
"""
Stage 3 — Manual Validation
Samples 10% of extracted records for spot-check against source text.
Outputs: data/processed/validation_report.json + logs/validation.log

Run interactively: python3 scripts/03_validate.py
"""

import json, random, os, sys
from datetime import datetime
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
CRITERIA_F  = BASE_DIR / "data/processed/criteria.json"
HAYDEN_2018 = BASE_DIR / "data/raw/hayden2018.txt"
OUTPUT_FILE = BASE_DIR / "data/processed/validation_report.json"
LOG_FILE    = BASE_DIR / "logs/stage3_validation.log"

CRITERIA_CODES = ["C01","C02","C03","C04","C05","C06","C07","C08","C09","C10","C11"]

CHAPTERS = {
    2: (1611, 3505), 3: (3505, 5463), 4: (5463, 6503), 5: (6503, 7954),
    6: (7954, 8367), 7: (8367, 10187), 8: (10187, 10464), 9: (10464, 11899),
}

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_society_excerpt(lines, society):
    ch = society.get("chapter", 2)
    start, end = CHAPTERS.get(ch, (0, len(lines)))
    text = "".join(lines[start-1:end-1])

    soc_name = society.get("society_name","").lower()
    idx = text.lower().find(soc_name)
    if idx == -1:
        return text[:3000]

    # Return ~1500 chars around first mention
    ctx_start = max(0, idx - 200)
    ctx_end   = min(len(text), idx + 1500)
    return text[ctx_start:ctx_end]

def main():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log("="*60)
    log("Stage 3: Manual Validation Spot-Check")
    log("="*60)

    records = json.load(open(CRITERIA_F, encoding="utf-8"))
    lines   = open(HAYDEN_2018, encoding="utf-8", errors="replace").readlines()

    # Sample 10% minimum 5, maximum 15
    n_sample = max(5, min(15, len(records) // 10))
    sample   = random.sample(records, n_sample)
    log(f"Sampling {n_sample} of {len(records)} records for validation")

    validation_results = []
    tp = fp = tn = fn = 0

    for i, rec in enumerate(sample):
        sid = rec["society_id"]
        soc_name = rec.get("society_name","")
        print(f"\n{'='*60}")
        print(f"[{i+1}/{n_sample}] {sid}: {soc_name}")
        print(f"Region: {rec.get('region')} | Ch.{rec.get('chapter')}")
        print(f"Institution type: {rec.get('institution_type')}")
        print(f"Documentation quality: {rec.get('documentation_quality')}")
        print()

        excerpt = get_society_excerpt(lines, rec)
        print("SOURCE TEXT EXCERPT:")
        print("-"*40)
        print(excerpt[:2000])
        print("-"*40)

        print("\nEXTRACTED CRITERIA:")
        criteria = rec.get("criteria", {})
        for code in CRITERIA_CODES:
            c = criteria.get(code, {})
            val = c.get("value", "missing") if isinstance(c, dict) else "missing"
            ev  = c.get("evidence","") if isinstance(c, dict) else ""
            print(f"  {code}: {val:10s} | {ev}")

        print("\nVALIDATION:")
        record_tps, record_fps, record_tns, record_fns = 0,0,0,0
        criterion_results = []

        for code in CRITERIA_CODES:
            c = criteria.get(code, {})
            extracted_val = c.get("value","unclear") if isinstance(c, dict) else "unclear"
            extracted_ev  = c.get("evidence","") if isinstance(c, dict) else ""

            ans = input(f"  {code} extracted='{extracted_val}'. Correct? (y/n/s=skip): ").strip().lower()
            if ans == "s":
                criterion_results.append({"code":code,"extracted":extracted_val,"validator":"skipped"})
                continue

            correct = ans == "y"
            if extracted_val in ("present","partial") and correct:
                record_tps += 1
            elif extracted_val in ("present","partial") and not correct:
                record_fps += 1
            elif extracted_val in ("absent","unclear") and correct:
                record_tns += 1
            elif extracted_val in ("absent","unclear") and not correct:
                record_fns += 1

            criterion_results.append({
                "code": code,
                "extracted": extracted_val,
                "extracted_evidence": extracted_ev,
                "validator_correct": correct,
            })

        notes = input("  Notes (or Enter to skip): ").strip()
        tp += record_tps; fp += record_fps
        tn += record_tns; fn += record_fns

        validation_results.append({
            "society_id": sid,
            "society_name": soc_name,
            "criteria_results": criterion_results,
            "notes": notes,
        })

        # Save after each record
        json.dump(validation_results,
                  open(OUTPUT_FILE,"w",encoding="utf-8"), indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"  Records checked: {n_sample}")
    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp+fp) > 0 else 0
    recall    = tp / (tp + fn) if (tp+fn) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision+recall) > 0 else 0
    print(f"  TP:{tp} FP:{fp} TN:{tn} FN:{fn}")
    print(f"  Precision: {precision:.2f}")
    print(f"  Recall:    {recall:.2f}")
    print(f"  F1:        {f1:.2f}")

    summary = {
        "n_sampled": n_sample, "n_total": len(records),
        "tp":tp,"fp":fp,"tn":tn,"fn":fn,
        "precision":round(precision,3),
        "recall":round(recall,3),
        "f1":round(f1,3),
        "results": validation_results,
        "timestamp": datetime.now().isoformat(),
    }
    json.dump(summary, open(OUTPUT_FILE,"w",encoding="utf-8"), indent=2, ensure_ascii=False)
    log(f"Validation report saved: {OUTPUT_FILE}")
    log(f"Precision={precision:.2f} Recall={recall:.2f} F1={f1:.2f}")

if __name__ == "__main__":
    main()
