with g as (
    select distinct genre_name from {{ ref('bridge_release_genre') }} where genre_name is not null
)
select md5(genre_name) as genre_key, genre_name from g
