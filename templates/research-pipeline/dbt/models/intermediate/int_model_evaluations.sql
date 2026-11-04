with staging as (
    select * from {{ ref('stg_evaluations') }}
)

select
    model_id,
    model_name,
    provider,
    model_type,
    case when model_type = 'open_weight' then 1 else 0 end as is_open_weight
from staging
