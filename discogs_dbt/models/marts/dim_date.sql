-- DIMENSION: year-grain time (Discogs dates are often partial) + Unknown member.
with y as (
    select distinct release_year
    from {{ ref('int_releases_cleaned') }}
    where release_year is not null
)
select md5(release_year::varchar) as year_key, release_year, (release_year/10)*10 as decade from y
union all
select md5('n/a') as year_key, null as release_year, null as decade
