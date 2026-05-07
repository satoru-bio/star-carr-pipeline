#!/usr/bin/env python3
"""
Stage 1 — Society Identification
Scans Hayden (2018) Chapters 2-9 and extracts named societies.
Outputs: data/processed/societies.json
"""

import json, os, re, sys, anthropic
from datetime import datetime
from pathlib import Path

def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in open(env_path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()

BASE_DIR    = Path(__file__).parent.parent
HAYDEN_2018 = BASE_DIR / "data/raw/hayden2018.txt"
OUTPUT_FILE = BASE_DIR / "data/processed/societies.json"
LOG_FILE    = BASE_DIR / "logs/stage1.log"

# Exact chapter start lines (1-indexed) from text analysis
CHAPTERS = {
    2:  (1611, "American Northwest Coast"),
    3:  (3505, "California"),
    4:  (5463, "American Southwest / Mesoamerica"),
    5:  (6503, "Plains North America"),
    6:  (7954, "Eastern Woodlands / Great Lakes"),
    7:  (8367, "Oceania / Melanesia"),
    8:  (10187, "Central Africa"),
    9:  (10464, "West Africa"),
    10: (11899, "STOP"),
}

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_chapter_text(lines, ch_num):
    start, region = CHAPTERS[ch_num]
    end = CHAPTERS.get(ch_num + 1, (len(lines)+1, ""))[0]
    return "".join(lines[start-1:end-1]), region

def parse_json(raw, ch_num):
    raw = re.sub(r'```json\s*|```', '', raw).strip()
    try:
        r = json.loads(raw)
        return r if isinstance(r, list) else []
    except Exception as e:
        log(f"  JSON error ch{ch_num}: {e} | {raw[:200]}")
        return []

SYSTEM = """Extract structured data from ethnographic text about secret societies.
For each distinct named society/ethnic group with documented secret society or restricted 
ritual institution activity, return a JSON array of objects with EXACTLY these fields:
{
  "society_name": "primary name",
  "ethnic_group": "broader ethnic group if different, else same as society_name",
  "subsistence_type": "complex hunter-gatherer|horticultural|pastoral|agricultural|mixed|unclear",
  "source_ethnographers": "comma-separated surnames",
  "documentation_quality": "rich|moderate|thin|unclear",
  "institution_type": "secret society|initiatory society|age-grade|shamanic sodality|ritual sodality|unclear",
  "notes": "one sentence describing the institution"
}
Return ONLY valid JSON array. No markdown, no explanation. [] if nothing qualifies.
Include only substantively documented cases (at least a paragraph), not passing mentions."""

def main():
    log("="*60)
    log("Stage 1: Society Identification — Hayden 2018 Ch.2-9")
    log("="*60)

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        log("ERROR: ANTHROPIC_API_KEY not set"); sys.exit(1)

    client = anthropic.Anthropic(api_key=key)
    lines  = open(HAYDEN_2018, encoding="utf-8", errors="replace").readlines()
    log(f"Loaded {len(lines)} lines")

    all_soc, sid = [], 1

    for ch in range(2, 10):
        text, region = get_chapter_text(lines, ch)
        words = text.split()
        if len(words) > 14000:
            text = " ".join(words[:14000])
            log(f"\nCh.{ch} {region} — truncated to 14k/{len(words)} words")
        else:
            log(f"\nCh.{ch} {region} — {len(words)} words")

        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=SYSTEM,
            messages=[{"role":"user","content":f"Chapter {ch} | Region: {region}\n\n{text}"}]
        )
        socs = parse_json(resp.content[0].text, ch)
        log(f"  -> {len(socs)} societies")

        for s in socs:
            s.update({"society_id": f"H18_{sid:03d}", "source_book": "Hayden 2018",
                       "chapter": ch, "region": region})
            all_soc.append(s)
            log(f"    {s['society_id']}: {s.get('society_name')} [{s.get('documentation_quality','?')}]")
            sid += 1

    log(f"\nTotal: {len(all_soc)} societies")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(all_soc, open(OUTPUT_FILE,"w",encoding="utf-8"), indent=2, ensure_ascii=False)
    log(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
