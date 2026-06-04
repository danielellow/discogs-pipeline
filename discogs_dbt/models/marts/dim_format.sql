-- DIMENSION: format with physical/digital class (+ Unknown member).
with f as (
    select distinct primary_format as format_name
    from {{ ref('int_releases_cleaned') }}
    where primary_format is not null
)
select
    md5(format_name) as format_key, format_name,
    case when format_name in ('File','FLAC','MP3','AAC') then 'Digital' else 'Physical' end as format_class
from f
union all
select md5('n/a') as format_key, 'Unknown' as format_name, 'Unknown' as format_class
