import duckdb
import glob
import os

# Connect to a DuckDB database file (created if it doesn't exist).
# This single file is the warehouse.
con = duckdb.connect("discogs.duckdb")

# Bronze layer: a 'raw' schema holding data exactly as it arrived.
con.execute("CREATE SCHEMA IF NOT EXISTS raw;")
con.execute("""
    CREATE OR REPLACE TABLE raw.releases_raw (
        source_label VARCHAR,   -- which label file this came from
        raw_data     JSON,      -- the full Discogs release, untouched
        _loaded_at   TIMESTAMP  -- when we loaded it (lineage)
    );
""")

# Find every .jsonl file across any ingest_date folder.
files = glob.glob("raw/discogs/releases/ingest_date=*/*.jsonl")
print(f"Found {len(files)} files to load.")

total = 0
for path in files:
    # label name = the filename without .jsonl (e.g. 'felt')
    label = os.path.basename(path).replace(".jsonl", "")
    with open(path) as f:
        rows = [(label, line.strip()) for line in f if line.strip()]
    con.executemany(
        "INSERT INTO raw.releases_raw VALUES (?, CAST(? AS JSON), now())",
        rows,
    )
    total += len(rows)
    print(f"  loaded {len(rows):>4} from {label}")

print(f"\nTotal rows loaded: {total}")

# Quick sanity checks
print("\nRow count per label:")
for label, n in con.execute(
    "SELECT source_label, COUNT(*) FROM raw.releases_raw "
    "GROUP BY source_label ORDER BY source_label"
).fetchall():
    print(f"  {label}: {n}")

print("\nPeek — pulling a few fields straight out of the JSON:")
for title, year, country in con.execute("""
    SELECT raw_data->>'$.title'   AS title,
           raw_data->>'$.year'    AS year,
           raw_data->>'$.country' AS country
    FROM raw.releases_raw
    LIMIT 5
""").fetchall():
    print(f"  {year}  {title}  ({country})")

con.close()
print("\nDone. Warehouse file: discogs.duckdb")