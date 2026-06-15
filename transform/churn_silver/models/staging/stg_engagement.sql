with source as (
    select * from read_parquet('../../data/bronze/engagement/**/*.parquet')
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
        engagement_id,
        customer_id,
        period_days::integer                            as period_days,
        total_logins_90d::integer                       as total_logins_90d,
        avg_logins_per_week::double                     as avg_logins_per_week,
        active_features::integer                        as active_features,
        feature_list,
        last_login_days_ago::integer                    as last_login_days_ago,
        api_calls_30d::integer                          as api_calls_30d,
        users_active_30d::integer                       as users_active_30d,
        case
            when avg_logins_per_week >= 3 then 'high'
            when avg_logins_per_week >= 1 then 'medium'
            else 'low'
        end                                             as engagement_level
    from deduped
    where rn = 1
      and customer_id is not null
)

select * from cleaned
