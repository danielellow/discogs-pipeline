-- INTERMEDIATE (silver): clean + derive. Dedup already done in staging.
with staged as (
    select * from {{ ref('stg_releases') }}
)
select
    release_id,
    source_label,
    nullif(trim(release_title), '')                     as release_title,
    release_year,
    try_strptime(released_raw, '%Y-%m-%d')::date        as released_date,
    upper(nullif(trim(country), ''))                    as country,
    primary_artist_name,
    primary_artist_id,
    primary_label_name,
    primary_label_id,
    primary_format,
    genres_json,
    community_have,
    community_want,
    rating_average,
    num_for_sale,
    case when community_have > 0
         then round(community_want * 1.0 / community_have, 2)
    end                                                 as want_to_have_ratio,
    thumb_url,
    discogs_uri,
    styles,
    _loaded_at                                          as source_loaded_at,
    'discogs_api'                                       as source_system
from staged
