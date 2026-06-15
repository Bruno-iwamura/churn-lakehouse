-- Customer 360: visão unificada de cada cliente
-- Este é o modelo central da Silver — une todos os silos numa única tabela
-- Uma linha por cliente com todos os atributos relevantes

with customers as (
    select * from {{ ref('stg_crm') }}
),

transactions as (
    select * from {{ ref('int_customer_transactions') }}
),

financial as (
    select * from {{ ref('int_customer_financial') }}
),

support as (
    select * from {{ ref('stg_support') }}
),

engagement as (
    select * from {{ ref('stg_engagement') }}
),

joined as (
    select
        -- identidade
        c.customer_id,
        c.company_name,
        c.industry,
        c.plan,
        c.city,
        c.state,
        c.employees_range,

        -- ciclo de vida
        c.acquisition_date,
        c.cancellation_date,
        c.churned,
        c.tenure_days,
        round(c.tenure_days / 30.0, 1)                 as tenure_months,

        -- financeiro
        f.current_mrr_brl,
        f.avg_mrr_brl,
        f.total_revenue_brl,
        f.total_expansion_brl,
        f.total_contraction_brl,
        f.mrr_drop_rate,

        -- pagamentos
        t.total_invoices,
        t.total_billed_brl,
        t.total_unpaid_brl,
        t.late_payment_rate,
        t.avg_days_late,
        t.max_days_late,
        t.months_with_discount,

        -- suporte
        s.nps_score,
        s.nps_category,
        s.total_tickets,
        s.open_tickets,
        s.open_ticket_rate,
        s.avg_resolution_hours,
        s.last_ticket_type,

        -- engajamento
        e.total_logins_90d,
        e.avg_logins_per_week,
        e.active_features,
        e.feature_list,
        e.last_login_days_ago,
        e.api_calls_30d,
        e.users_active_30d,
        e.engagement_level

    from customers c
    left join transactions t  on c.customer_id = t.customer_id
    left join financial    f  on c.customer_id = f.customer_id
    left join support      s  on c.customer_id = s.customer_id
    left join engagement   e  on c.customer_id = e.customer_id
)

select * from joined
