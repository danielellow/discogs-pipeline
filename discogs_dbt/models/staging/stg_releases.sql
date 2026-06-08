-- STAGING (bronze->silver edge): flatten the JSON, type + rename.
-- Deduplication happens here at the source: Discogs returns some releases more
-- than once, so keeping one row per release id (most recently loaded) before
-- extracting fields. (Doing it pre-extraction keeps the window simple)
with source as (
    select *
    from {{ source('raw', 'releases_raw') }}
    where raw_data->>'$.id' is not null
    qualify row_number() over (
        partition by raw_data->>'$.id'
        order by _loaded_at desc
    ) = 1
)
select
    (raw_data->>'$.id')::bigint                         as release_id,
    source_label,
    raw_data->>'$.title'                                as release_title,
    try_cast(nullif(raw_data->>'$.year', '0') as int)  as release_year,
    raw_data->>'$.released'                             as released_raw,
    raw_data->>'$.country'                              as country,
    raw_data->>'$.artists[0].name'                      as primary_artist_name,
    (raw_data->>'$.artists[0].id')::bigint              as primary_artist_id,
    raw_data->>'$.labels[0].name'                       as primary_label_name,
    (raw_data->>'$.labels[0].id')::bigint               as primary_label_id,
    raw_data->>'$.formats[0].name'                      as primary_format,
    raw_data->'$.genres'                                as genres_json,
    (raw_data->>'$.community.have')::int                as community_have,
    (raw_data->>'$.community.want')::int                as community_want,
    (raw_data->>'$.community.rating.average')::double   as rating_average,
    (raw_data->>'$.num_for_sale')::int                  as num_for_sale,
    raw_data->>'$.thumb'                                as thumb_url,
    raw_data->>'$.uri'                                  as discogs_uri,
    array_to_string(cast(raw_data->'$.styles' as varchar[]), ', ') as styles,
    _loaded_at
from source
