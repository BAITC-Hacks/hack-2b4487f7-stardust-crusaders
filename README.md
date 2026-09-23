# hack-2b4487f7-stardust-crusaders
Hackathon team repository for Stardust Crusaders

## Dataset audit

Run `python scripts/audit_dataset.py` (Python 3.8+, standard library only).
The script reads `data/hackathon_dataset_anonymized.csv`, falling back to
`data/hackathon-dataset-anonymized.csv` only if the first file is absent.
Paths are resolved relative to the script, regardless of the working directory.
The dataset is never modified. An empty or invalid CSV produces an error and exit code 1.

The report includes unique pipe-separated values, profile counts, category/city
coverage, the top 10 categories by profile count, rare categories (<= 3 profiles),
and busy-day statistics. Duplicate values within a profile count once.
Empty `max_hours` is accepted; missing values are reported separately.
Dates must use `YYYY-MM-DD`; December statistics include all years and all
profiles, including those with no busy dates (zero days). Boolean fields accept
case-insensitive `true`/`false` or blanks; blank flags are not counted as true.
