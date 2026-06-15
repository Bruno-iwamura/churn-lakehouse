with source as (
    select * from read_parquet('../../data/bronze/crm/**/*.parquet')
),

deduped as (
    select *,
        row_number() over (
            partition by customer_id
            order by _ingested_at desc
        ) as rn
    from source
),

cleaned as (
    select
        customer_id,
        company_name,
        industry,
        plan,
        acquisition_date::date                          as acquisition_date,
        cancellation_date::date                         as cancellation_date,
        churned::boolean                                as churned,
        city,
        state,
        employees_range,
        case
            when churned = true
            then datediff('day', acquisition_date::date, cancellation_date::date)
            else datediff('day', acquisition_date::date, current_date)
        end                                             as tenure_days
    from deduped
    where rn = 1
      and customer_id is not null
)

select * from cleaned
