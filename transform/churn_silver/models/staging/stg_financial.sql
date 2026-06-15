with source as (
    select * from read_parquet('../../data/bronze/financial/**/*.parquet')
),

cleaned as (
    select
        financial_id,
        customer_id,
        month,
        plan,
        mrr_brl::double                                 as mrr_brl,
        expansion_brl::double                           as expansion_brl,
        contraction_brl::double                         as contraction_brl,
        churned_revenue_brl::double                     as churned_revenue_brl,
        mrr_brl + expansion_brl - contraction_brl       as net_mrr_brl
    from source
    where customer_id is not null
      and mrr_brl > 0
)

select * from cleaned
