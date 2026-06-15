-- Agrega o histórico financeiro mensal por cliente
-- Captura tendência de MRR e sinais de downgrade

with financial as (
    select * from {{ ref('stg_financial') }}
),

aggregated as (
    select
        customer_id,

        -- MRR
        max(mrr_brl)                                    as current_mrr_brl,
        avg(mrr_brl)                                    as avg_mrr_brl,
        min(mrr_brl)                                    as min_mrr_brl,
        sum(mrr_brl)                                    as total_revenue_brl,

        -- expansão e contração
        sum(expansion_brl)                              as total_expansion_brl,
        sum(contraction_brl)                            as total_contraction_brl,
        sum(churned_revenue_brl)                        as total_churned_revenue_brl,

        -- sinal de downgrade: MRR mínimo muito menor que MRR atual
        round(
            (max(mrr_brl) - min(mrr_brl))
            / nullif(max(mrr_brl), 0), 4
        )                                               as mrr_drop_rate,

        count(distinct month)                           as active_months

    from financial
    group by customer_id
)

select * from aggregated
