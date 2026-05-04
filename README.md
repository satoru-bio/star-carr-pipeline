# star-carr-pipeline

LLM-assisted extraction and comparative coding of secret society material criteria from Hayden (2018) — ethnographic baseline dataset for the Star Carr paper.

## Overview

This repository contains the data extraction pipeline and coded comparative dataset for:

> Langley, A. (in prep.). The Threshold Society: Applying Hayden's Secret Society Model to the Mesolithic Site of Star Carr. *Cambridge Archaeological Journal*.

Using a two-stage LLM pipeline (Claude Haiku for society identification, Claude Sonnet for criteria extraction), 84 documented secret society cases were coded against 11 material and spatial criteria derived from Hayden's (2018) *The Power of Ritual in Prehistory*, Chapters 2–9. The resulting frequency table provides an empirical ethnographic baseline against which the Star Carr archaeological evidence profile is evaluated.

## Repository Structure

scripts/          — Pipeline scripts 01–05
data/
processed/      — Output datasets (societies.json, criteria.json, merged_dataset.csv)
figures/        — Paper figure (fig_comparative_criteria.png) and frequency table CSV
output/           — Analysis summary and methods note
requirements.txt  — Python dependencies
.env.template     — Environment variable template

## Source Data

The pipeline extracts text from:

- Hayden, B. 2018. *The Power of Ritual in Prehistory: Secret Societies and Origins of Social Complexity*. Cambridge: Cambridge University Press. Chapters 2–9.

The raw source text is **not included** in this repository for copyright reasons. To reproduce the extraction, obtain a copy of the book and extract the text locally:

```bash
# Linux/Mac
pdftotext hayden2018.pdf data/raw/hayden2018.txt

# Windows (using pdfminer)
pip install pdfminer.six
python -c "
from pdfminer.high_level import extract_text
text = extract_text('hayden2018.pdf')
open('data/raw/hayden2018.txt', 'w', encoding='utf-8').write(text)
"
```

## 11 Criteria

**Core (map to Star Carr application):**

| Code | Criterion |
|------|-----------|
| C01 | Transformation symbolism |
| C02 | Feasting |
| C03 | Exotic/prestige materials |
| C04 | Spatial liminality |
| C05 | Long-duration institutional use |
| C06 | Burial absence from ritual locus |

**Extended (from Hayden Ch.10 material patterns):**

| Code | Criterion |
|------|-----------|
| C07 | Special structure |
| C08 | Remote locations |
| C09 | Ritual paraphernalia cache |
| C10 | Power animal iconography |
| C11 | Interaction sphere |

## Pipeline Stages

| Script | Function | Model | Runtime |
|--------|----------|-------|---------|
| `01_identify_societies.py` | Society identification, Ch.2–9 | Claude Haiku | ~5 min |
| `02_extract_criteria.py` | 11-criterion extraction per society | Claude Sonnet | ~30–40 min |
| `03_validate.py` | Interactive spot-check, 10% sample | Manual | ~45 min |
| `04_dplace_merge.py` | D-PLACE EA072 merge, flat CSV output | — | ~2 min |
| `05_analyse_and_figure.py` | Frequency table + paper figure (300 DPI) | — | ~1 min |

Stage 2 is resumable — safe to interrupt and restart.

## Setup

```bash
cp .env.template .env
# Add your ANTHROPIC_API_KEY to .env

pip install -r requirements.txt

python scripts/01_identify_societies.py
python scripts/02_extract_criteria.py
python scripts/03_validate.py      # interactive
python scripts/04_dplace_merge.py
python scripts/05_analyse_and_figure.py
```

## Results

Across 84 documented secret society cases (Hayden 2018, Ch.2–9):

- Star Carr meets **10 of 11 criteria**
- Mean baseline frequency across all criteria: **85.9%**
- Star Carr meets or exceeds the baseline on every assessable criterion

See `output/analysis_summary.txt` for the full frequency table and `data/figures/fig_comparative_criteria.png` for the paper figure.

## Validation

Manual spot-check validation of 10% of extracted records (n=8) was conducted against source text prior to analysis. The validation report is available at `data/processed/validation_report.json`.

## Citation

If using this dataset or pipeline, please cite:

> Langley, A. (in prep.). The Threshold Society: Applying Hayden's Secret Society Model to the Mesolithic Site of Star Carr. *Cambridge Archaeological Journal*.

Dataset DOI: [to be assigned on Zenodo deposition]

## Licence

Code: MIT  
Data: CC BY 4.0  
Source text (Hayden 2018): not included — copyright Cambridge University Press

## Author

Dr Andrew Langley  
DigiShield Labs Ltd  
[satoru.bio](https://satoru.bio)
