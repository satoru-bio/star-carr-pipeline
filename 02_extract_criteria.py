#!/usr/bin/env python3
"""
Stage 2 — Criteria Extraction
For each society in societies.json, extracts 11 material criteria from the source text.
Outputs: data/processed/criteria.json

11 criteria:
  Core (map to Star Carr application):
    C01 transformation_symbolism
    C02 feasting
    C03 exotic_prestige_materials
    C04 spatial_liminality
    C05 long_duration_institutional
    C06 burial_absence_from_ritual_locus
  Extended (from Hayden Ch.10 material patterns):
    C07 special_structure
    C08 remote_locations
    C09 ritual_paraphernalia_cache
    C10 power_animal_iconography
    C11 interaction_sphere
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
SOCIETIES   = BASE_DIR / "data/processed/societies.json"
OUTPUT_FILE = BASE_DIR / "data/processed/criteria.json"
LOG_FILE    = BASE_DIR / "logs/stage2.log"

CHAPTERS = {
    2: (1611, 3505), 3: (3505, 5463), 4: (5463, 6503), 5: (6503, 7954),
    6: (7954, 8367), 7: (8367, 10187), 8: (10187, 10464), 9: (10464, 11899),
}

CRITERIA = [
    ("C01","transformation_symbolism",
     "Objects/practices enabling identity boundary-crossing between human and non-human "
     "(masks, costumes, therianthropic transformation). Frontlets, animal skins, masks worn "
     "in ritual contexts."),
    ("C02","feasting",
     "Large-scale food consumption beyond subsistence need, associated with ritual events. "
     "Initiation feasts, inter-community feasts, surplus food preparation at ritual sites."),
    ("C03","exotic_prestige_materials",
     "Non-local materials aggregated at restricted loci: shells, copper, crystals, rare stones, "
     "imported goods used in ritual rather than domestic contexts."),
    ("C04","spatial_liminality",
     "Site location at threshold between categories: water margins, caves, forest edges, "
     "underground spaces. Deliberate architectural investment in liminal space."),
    ("C05","long_duration_institutional",
     "Multi-generational use of the same locus or institution. Architectural maintenance, "
     "hereditary roles, institutionalised return across generations."),
    ("C06","burial_absence",
     "Mortuary practice separated from ritual locus. Dead buried in community/domestic "
     "contexts, not at restricted ritual sites."),
    ("C07","special_structure",
     "Purpose-built structure for restricted ritual use: kivas, cult houses, dance houses, "
     "men's houses, ceremonial lodges distinct from residential architecture."),
    ("C08","remote_locations",
     "Secondary ritual locations at distance from community: bush schools, mountaintop shrines, "
     "isolated camps, caves used for initiation seclusion."),
    ("C09","ritual_paraphernalia_cache",
     "Stored or cached ritual objects kept secret from non-initiates: masks, costumes, "
     "sacred bundles, instruments hidden between ceremonies."),
    ("C10","power_animal_iconography",
     "Non-prey animal iconography: carnivores, raptors, imaginary animals depicted in "
     "threatening poses. Therianthropic imagery. Not staple food species."),
    ("C11","interaction_sphere",
     "Evidence of regional networks sharing ritual materials or iconography across "
     "ethnic/linguistic boundaries: common motifs, traded ritual objects, shared ceremonies."),
]

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_chapter_text(lines, ch_num):
    start, end = CHAPTERS.get(ch_num, (0, len(lines)))
    return "".join(lines[start-1:end-1])

def parse_json(raw, sid):
    raw = re.sub(r'```json\s*|```', '', raw).strip()
    try:
        r = json.loads(raw)
        return r if isinstance(r, dict) else {}
    except Exception as e:
        log(f"  JSON error {sid}: {e}")
        return {}

SYSTEM = """You are a careful research assistant extracting structured comparative data.
Given ethnographic text about a specific society and a list of material/spatial criteria,
assess whether each criterion is present for that society.

For each criterion, respond with:
- "present", "absent", "partial", or "unclear"
- A brief evidence note (max 20 words) citing what the text says

Return ONLY a valid JSON object with criterion codes as keys:
{
  "C01": {"value": "present|absent|partial|unclear", "evidence": "brief note"},
  "C02": {"value": "...", "evidence": "..."},
  ... (all 11 criteria)
}
No markdown, no explanation outside the JSON."""

def extract_criteria(client, society, text):
    criteria_desc = "\n".join(
        f"{code} — {name}: {desc}"
        for code, name, desc in CRITERIA
    )

    # Locate society-specific text within chapter
    # Search for society name to get a focused excerpt
    soc_name = society.get("society_name", "")
    ethnic    = society.get("ethnic_group", "")

    # Try to find a focused passage (~3000 words around the society's name)
    words = text.split()
    text_lower = text.lower()
    search_terms = [soc_name.lower(), ethnic.lower()]
    best_pos = None
    for term in search_terms:
        if term and len(term) > 3:
            idx = text_lower.find(term)
            if idx != -1:
                # Convert char position to approximate word position
                word_pos = len(text[:idx].split())
                best_pos = max(0, word_pos - 200)
                break

    if best_pos is not None:
        excerpt_words = words[best_pos:best_pos+4000]
    else:
        excerpt_words = words[:4000]
    excerpt = " ".join(excerpt_words)

    user_msg = (
        f"Society: {soc_name} (ethnic group: {ethnic})\n"
        f"Region: {society.get('region')}\n\n"
        f"CRITERIA TO ASSESS:\n{criteria_desc}\n\n"
        f"TEXT EXCERPT:\n{excerpt}"
    )

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM,
        messages=[{"role":"user","content":user_msg}]
    )
    return parse_json(resp.content[0].text, society.get("society_id"))

def main():
    log("="*60)
    log("Stage 2: Criteria Extraction")
    log("="*60)

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        log("ERROR: ANTHROPIC_API_KEY not set"); sys.exit(1)

    societies = json.load(open(SOCIETIES, encoding="utf-8"))
    log(f"Loaded {len(societies)} societies")

    client = anthropic.Anthropic(api_key=key)
    lines  = open(HAYDEN_2018, encoding="utf-8", errors="replace").readlines()

    # Load existing results to allow resuming
    if OUTPUT_FILE.exists():
        results = json.load(open(OUTPUT_FILE, encoding="utf-8"))
        done_ids = {r["society_id"] for r in results}
        log(f"Resuming — {len(done_ids)} already processed")
    else:
        results, done_ids = [], set()

    chapter_cache = {}

    for i, soc in enumerate(societies):
        sid = soc["society_id"]
        if sid in done_ids:
            continue

        ch = soc.get("chapter", 2)
        if ch not in chapter_cache:
            chapter_cache[ch] = get_chapter_text(lines, ch)
        text = chapter_cache[ch]

        log(f"\n[{i+1}/{len(societies)}] {sid}: {soc.get('society_name')}")
        criteria_data = extract_criteria(client, soc, text)

        record = {**soc, "criteria": criteria_data}
        results.append(record)
        done_ids.add(sid)

        # Save after each record (allows resuming)
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        json.dump(results, open(OUTPUT_FILE,"w",encoding="utf-8"), indent=2, ensure_ascii=False)

        # Log summary
        if criteria_data:
            present = sum(1 for v in criteria_data.values()
                         if isinstance(v, dict) and v.get("value") in ("present","partial"))
            log(f"  Criteria met (present/partial): {present}/11")

    log(f"\nComplete. {len(results)} records saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
