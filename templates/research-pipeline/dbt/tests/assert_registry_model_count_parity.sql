-- Singular deterministic test: Assert that total models counted across marts
-- equals total distinct models registered in the registry seed.
with registry_count as (
    select count(distinct model_id) as cnt from {{ ref('safety_model_registry') }}
),
mart_count as (
    select coalesce(sum(total_models), 0) as cnt from {{ ref('fct_evaluation_summary') }}
)
select
    registry_count.cnt as registry_cnt,
    mart_count.cnt as mart_cnt
from registry_count
cross join mart_count
where registry_count.cnt != mart_count.cnt
