-- FACT (gold). Grain: one row per release. Surrogate PK + FKs + measures.
with releases as (
    select * from {{ ref('int_releases_cleaned') }}
)
select
    md5(release_id::varchar)                         as release_key,
    md5(coalesce(primary_artist_id::varchar, 'n/a')) as artist_key,
    md5(coalesce(primary_label_id::varchar, 'n/a'))  as label_key,
    md5(coalesce(release_year::varchar, 'n/a'))      as year_key,
    md5(coalesce(primary_format, 'n/a'))             as format_key,
    release_id,
    release_title,
    source_label,
    country,
    thumb_url,
    discogs_uri,
    styles,
    -- additive measures
    community_have,
    -- additive measures
    community_have,
    community_want,
    num_for_sale,
    -- non-additive measures (never SUM these)
    rating_average,
    want_to_have_ratio,
    source_loaded_at,
    source_system
from releases
