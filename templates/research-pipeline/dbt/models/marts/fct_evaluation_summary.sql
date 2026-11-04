with evaluations as (
    select * from {{ ref('int_model_evaluations') }}
)

select
    model_type,
    count(distinct model_id) as total_models,
    sum(is_open_weight) as open_weight_count
from evaluations
group by model_type
