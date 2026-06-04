-- DIMENSION: artist. One row per artist_id (Discogs sometimes spells the same
-- artist differently across releases, so we collapse to one name per id).
-- Includes an "Unknown" member for releases with missing artist data.
with a as (
    select
        primary_artist_id        as artist_id,
        min(primary_artist_name) as artist_name   -- one deterministic name per id
    from {{ ref('int_releases_cleaned') }}
    where primary_artist_id is not null
    group by primary_artist_id
)
select md5(artist_id::varchar) as artist_key, artist_id, artist_name from a
union all
select md5('n/a') as artist_key, null as artist_id, 'Unknown' as artist_name