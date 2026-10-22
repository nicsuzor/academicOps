with source as (
    select * from {{ ref('safety_model_registry') }}
)

select
    cast(model_id as string) as model_id,
    cast(model_name as string) as model_name,
    cast(provider as string) as provider,
    cast(model_type as string) as model_type,
    cast(release_date as string) as release_date
from source
