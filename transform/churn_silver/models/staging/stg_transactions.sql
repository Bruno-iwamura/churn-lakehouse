with source as (
    select * from read_parquet('../../data/bronze/transactions/**/*.parquet')
),

deduped as (
    select *,
        row_number() over (
            partition by transaction_id
            order by _ingested_at desc
        ) as rn
    from source
),

cleaned as (
    select
        transaction_id,
        customer_id,
        invoice_date::date                              as invoice_date,
        due_date::date                                  as due_date,
        paid_date::date                                 as paid_date,
        amount_brl::double                              as amount_brl,
        amount_paid_brl::double                         as amount_paid_brl,
        days_late::integer                              as days_late,
        status,
        discount_pct::integer                           as discount_pct,
        case when days_late > 0 then true else false
        end                                             as is_late,
        case when days_late > 30 then true else false
        end                                             as is_severely_late,
        amount_brl - amount_paid_brl                    as amount_unpaid_brl
    from deduped
    where rn = 1
      and customer_id is not null
      and amount_brl > 0
)

select * from cleaned
