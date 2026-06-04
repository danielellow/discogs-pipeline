-- Resolves the release<->genre many-to-many (a release can have several genres).
with r as (
    select release_id, genres_json from {{ ref('int_releases_cleaned') }}
),
unnested as (
    select release_id, unnest(cast(genres_json as varchar[])) as genre_name from r
)
select md5(release_id::varchar) as release_key, md5(genre_name) as genre_key, release_id, genre_name
from unnested
