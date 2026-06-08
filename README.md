# Discogs Desire Index - a data pipeline

An end-to-end data pipeline that pulls release data from the Discogs API for four
independent record labels, transforms it into a tested star schema, and visualises a
**"desire index"** — which records are most wanted relative to how few people actually
own them (the want-to-have ratio), divded by format, genre, label and year.

Built for course 7: Data Engineering, at Hyper Island's Data Analyst Program (DA27) by Daniel Ellow

## Pipeline flow

```
Discogs API
   │   ingest_discogs.py   (Python: paginated, rate-limit aware, resilient to errors)
   ▼
Raw JSON               raw/discogs/releases/ingest_date=YYYY-MM-DD/*.jsonl   (immutable, date-partitioned)
   │   load_to_duckdb.py
   ▼
DuckDB  (bronze)       raw.releases_raw   — release JSON stored as-is
   │   dbt  (staging → intermediate → marts)
   ▼
DuckDB  (gold)         star schema: fct_release + dim_artist / dim_label / dim_genre /
   │                   dim_date / dim_format, plus bridge_release_genre
   ▼
Streamlit app          a browsable "wall" of releases, querying the gold layer live

         orchestrated end-to-end by a scheduled GitHub Actions workflow
         (.github/workflows/pipeline.yml — daily cron + manual trigger)
```

## Tools per stage

| Stage | Tool |
|---|---|
| Source | Discogs REST API |
| Ingestion | Python (`requests`) |
| Raw storage | Date-partitioned JSON → DuckDB bronze table |
| Warehouse | DuckDB |
| Transformation | dbt (Core + dbt-duckdb) |
| Visualization | Streamlit (queries the warehouse directly, no CSV export) |
| Orchestration | GitHub Actions (scheduled) |

## Medallion architecture, documentation & tests

- **Bronze:** `raw.releases_raw` — raw API responses, untouched.
- **Silver:** `stg_releases` (flatten/type) → `int_releases_cleaned` (dedupe, clean, derive
  the want-to-have ratio).
- **Gold:** `fct_release` (grain: one release) + conformed dimensions.
- **Documentation & tests:** `discogs_dbt/models/marts/_marts.yml` — table/column
  descriptions plus `unique`, `not_null` and `relationships` tests (22 models + tests pass).

## Running it locally

```bash
pip install requests python-dotenv duckdb dbt-duckdb streamlit
# create a .env file with:  DISCOGS_TOKEN=your_token

python ingest_discogs.py                      # pull from the API → raw JSON
python load_to_duckdb.py                       # load raw JSON → DuckDB bronze
cd discogs_dbt && dbt build --profiles-dir .   # transform + test → star schema
cd .. && streamlit run app.py                  # explore the desire index
```

## Repository structure

```
.
├── ingest_discogs.py          # ingestion
├── load_to_duckdb.py          # raw → bronze
├── app.py                     # Streamlit visualization
├── discogs_dbt/               # dbt project (models, tests, docs)
├── .github/workflows/         # scheduled pipeline (GitHub Actions)
├── decision_log.md            # design decisions & trade-offs
└── (gitignored: .env, discogs.duckdb, raw/)
```


