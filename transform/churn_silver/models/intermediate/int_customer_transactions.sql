-- Agrega o histórico de transações por cliente
-- Transforma ~47k linhas em 1 linha por cliente com métricas de pagamento

with transactions as (
    select * from {{ ref('stg_transactions') }}
),

aggregated as (
    select
        customer_id,

        -- volume
        count(*)                                        as total_invoices,
        sum(amount_brl)                                 as total_billed_brl,
        sum(amount_paid_brl)                            as total_paid_brl,
        sum(amount_unpaid_brl)                          as total_unpaid_brl,

        -- comportamento de pagamento
        sum(case when is_late then 1 else 0 end)        as late_payments,
        sum(case when is_severely_late then 1 else 0
            end)                                        as severely_late_payments,
        round(
            sum(case when is_late then 1 else 0 end)
            ::double / count(*), 4
        )                                               as late_payment_rate,
        avg(days_late)                                  as avg_days_late,
        max(days_late)                                  as max_days_late,

        -- descontos de retenção
        sum(case when discount_pct > 0 then 1 else 0
            end)                                        as months_with_discount,
        avg(discount_pct)                               as avg_discount_pct

    from transactions
    group by customer_id
)

select * from aggregated
