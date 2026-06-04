-- DIMENSION: label. One row per label_id (+ Unknown member).
with l as (
    select
        primary_label_id        as label_id,
        min(primary_label_name) as label_name
    from {{ ref('int_releases_cleaned') }}
    where primary_label_id is not null
    group by primary_label_id
)
select md5(label_id::varchar) as label_key, label_id, label_name from l
union all
select md5('n/a') as label_key, null as label_id, 'Unknown' as label_name