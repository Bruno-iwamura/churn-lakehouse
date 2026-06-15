with source as (
    select * from read_parquet('../../data/bronze/support/**/*.parquet')
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
        support_id,
        customer_id,
        nps_score::integer                              as nps_score,
        nps_category,
        total_tickets::integer                          as total_tickets,
        open_tickets::integer                           as open_tickets,
        avg_resolution_hours::double                    as avg_resolution_hours,
        last_ticket_type,
        case
            when total_tickets > 0
            then round(open_tickets::double / total_tickets, 4)
            else 0
        end                                             as open_ticket_rate
    from deduped
    where rn = 1
      and customer_id is not null
)

select * from cleaned
