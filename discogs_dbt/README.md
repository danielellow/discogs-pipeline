# discogs_dbt — transformation layer (dbt Core + DuckDB)

Turns the bronze table `raw.releases_raw` into a tested star schema.

## Layers
- staging/      stg_releases            (view)  — flatten JSON, type, rename
- intermediate/ int_releases_cleaned    (view)  — clean, derive want_to_have_ratio
- marts/        fct_release             (table) — grain: one row per release
                dim_artist / dim_label / dim_genre / dim_date / dim_format
                bridge_release_genre            — release<->genre many-to-many

## Run it
From inside this folder:
    dbt build --profiles-dir .

(`dbt build` = run models + run tests in one go. Or run them separately:
 `dbt run --profiles-dir .` then `dbt test --profiles-dir .`.)

Browse the docs/lineage graph:
    dbt docs generate --profiles-dir .
    dbt docs serve --profiles-dir .

## Connection
profiles.yml points at ../discogs.duckdb — i.e. this project folder must sit
INSIDE the `pipeline` folder, next to discogs.duckdb. If your warehouse file is
elsewhere, edit the `path:` line in profiles.yml.
