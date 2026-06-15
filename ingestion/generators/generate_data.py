"""
Gerador de dados fictícios para o projeto Churn Lakehouse.
 
Este script cria cinco silos de dados simulando uma empresa SaaS B2B:
  - CRM:         clientes, planos, datas de aquisição
  - Transacional: faturas e pagamentos
  - Suporte:      tickets e NPS
  - Engajamento:  logins e uso de features
  - Financeiro:   MRR mensal por cliente
 
A lógica central: cada cliente recebe um "churn_score" latente (0-1).
Clientes com score alto têm comportamentos piores em todos os silos —
isso simula correlações reais que o modelo de ML vai aprender.
"""

import random
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
from faker import Faker  # type: ignore

# Configurações

SEED = 42
NUM_CUSTOMERS = 2000
OUTPUT_DIR = Path(__file__).resolve().parents[2]/"data"/"raw"

random.seed(SEED)
fake = Faker("pt_BR")
fake.seed_instance(SEED)

PLANS = {
    "starter":    {"mrr": 299,  "weight": 0.40},
    "growth":     {"mrr": 899,  "weight": 0.35},
    "pro":        {"mrr": 1_899, "weight": 0.20},
    "enterprise": {"mrr": 4_999, "weight": 0.05},
}

INDUSTRIES = [
    "Varejo", "Saúde", "Educação", "Tecnologia", "Financeiro",
    "Logística", "Agronegócio", "Serviços", "Indústria", "RH",
]

# FUNÇÕES

def weighted_choice(options: dict) -> str:
    """Escolhe uma chave do dicionário usando os pesos definidos em 'weight'."""
    keys = list(options.keys())
    weights = [v["weight"] for v in options.values()]
    return random.choices(keys, weights=weights, k=1)[0]

def random_date(start: date, end: date) -> date:
    """Gera uma data aleatória entre 'start' e 'end'."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

def churn_noise(base: float, noise: float = 0.15) -> float:
    """Adiciona ruído gaussiano a um valor base, mantendo entre 0 e 1."""
    return max(0.0, min(1.0, base + random.gauss(0, noise)))

# Gerador CRM

def generate_crm(customers: list[dict]) -> pd.DataFrame:
    "Tabela inicial de clientes. o campo churned é a variavel alvo do modelo de ML"

    rows = []
    for c in customers:
        rows.append({
            "customer_id": c["customer_id"],
            "company_name": fake.company(),
            "industry": random.choice(INDUSTRIES),
            "plan": c["plan"],
            "acquisition_date": c["acquisition_date"].isoformat(),
            "cancellation_date": c["cancellation_date"].isoformat() if c["churned"] else None,
            "churned": c["churned"],
            "city": fake.city(),
            "state": fake.estado_sigla(),
            "employees_range": random.choice(["1-10", "11-50", "51-200", "201-500", "500+"]),
        })
    return pd.DataFrame(rows)

# Gerador Transacional

def generate_transactions(customers: list[dict]) -> pd.DataFrame:
    """
    Faturas mensais por cliente
    Clientes com churn_score alto tem mais atrasos e inadimplências
    """

    rows = []
    today = date.today()


    for c in customers:
        tenure_months = c["tenure_months"]
        mrr = PLANS[c["plan"]]["mrr"]
        cs = c["churn_score"]

        for month_offset in range(tenure_months):
            invoice_date = c["acquisition_date"] + timedelta(days=30 * month_offset)
            if invoice_date > today:
                break

            # lógica: probabilidade de atraso e inadimplência aumenta com churn_score
            is_late = random.random() < (cs * 0.5)
            days_late = random.randint(5, 45) if is_late else 0

            # desconto ocasional (retention offer) — mais comum em clientes em risco
            discount_pct = random.choice([0, 0, 0, 10, 20]) if cs > 0.6 else random.choice([0, 0, 10])
            amount_paid = mrr * (1 - discount_pct / 100) if days_late == 0 else 0

            rows.append({
                "transaction_id": fake.uuid4(),
                "customer_id": c["customer_id"],
                "invoice_date": invoice_date.isoformat(),
                "due_date": (invoice_date + timedelta(days=10)).isoformat(),
                "paid_date": (invoice_date + timedelta(days=10 + days_late)).isoformat() if days_late > 0 else invoice_date.isoformat(),
                "amount_brl": mrr,
                "amount_paid_brl": round(amount_paid, 2),
                "days_late": days_late,
                "status": "late" if days_late > 0 else "paid",
                "discount_pct": discount_pct,
            })
    return pd.DataFrame(rows)

# Gerador Suporte

def generate_support(customers: list[dict]) -> pd.DataFrame:
#Tickets de suporte e NPS por cliente
#Clientes insatisfeitos (churn_score alto) abrem mais tickets criticos e dão NPS mais baixo

    ticket_types = ["bug", "dúvida", "lentidão", "integração", "cobrança","cancelamento"]
    type_weights_high = [0.30, 0.10, 0.20, 0.15, 0.15, 0.10]  # mais bugs e cancelamento
    type_weights_low  = [0.10, 0.35, 0.15, 0.25, 0.10, 0.05]  # mais dúvidas normais
 
    rows = []
    for c in customers:
        cs = c["churn_score"]
        # clientes insatisfeitos abrem mais tickets
        n_tickets = int(random.gauss(cs * 8 + 1, 1.5))
        n_tickets = max(0, min(n_tickets, 20))  # garantir não negativo e limite máximo

        #NPS: inversamente correlacionado com churn_score
        nps_base = 9 - int(cs * 7)
        nps = max(0, min(10, int(random.gauss(nps_base, 1.2))))

        rows.append({
            "support_id":      fake.uuid4(),
            "customer_id":     c["customer_id"],
            "nps_score":       nps,
            "nps_category":    "promoter" if nps >= 9 else ("neutral" if nps >= 7 else "detractor"),
            "total_tickets":   n_tickets,
            "open_tickets":    max(0, int(n_tickets * cs * 0.3)),
            "avg_resolution_hours": round(random.gauss(cs * 30 + 4, 5), 1),
            "last_ticket_type": random.choices(
                ticket_types,
                weights=type_weights_high if cs > 0.5 else type_weights_low
            )[0],
            "period":          c["acquisition_date"].isoformat(),
        })

    return pd.DataFrame(rows)

# Gerador Engajamento

def generate_engagement(customers: list[dict]) -> pd.DataFrame:
    """
    Métricas de uso do produto (últimos 90 dias).
    Clientes em risco de churn reduzem o uso antes de cancelar —
    esse é um dos sinais mais fortes para o modelo.
    """
    features = ["relatorios", "dashboard", "api", "exportacao", "usuarios", "integracao"]
 
    rows = []
    for c in customers:
        cs = c["churn_score"]
 
        # Logins caem com churn_score
        avg_logins = max(0, int(random.gauss(30 - cs * 25, 5)))
        # Features ativas (de 6 possíveis): menos features = mais risco
        active_features = max(0, int(random.gauss(6 - cs * 4, 1)))
        active_features = min(active_features, len(features))
 
        rows.append({
            "engagement_id": fake.uuid4(),
            "customer_id": c["customer_id"],
            "period_days": 90,
            "total_logins_90d": avg_logins * 3,
            "avg_logins_per_week": round(avg_logins / 12, 1),
            "active_features": active_features,
            "feature_list": ",".join(random.sample(features, active_features)) if active_features > 0 else "none",
            "last_login_days_ago": int(abs(random.gauss(cs * 25 + 1, 5))),
            "api_calls_30d": max(0, int(random.gauss(500 - cs * 450, 100))),
            "users_active_30d": max(1, int(random.gauss(10 - cs * 8, 2))),
        })
    return pd.DataFrame(rows)
    
# Gerador Financeiro
def generate_financial(customers: list[dict]) -> pd.DataFrame:
    """
    Resumo financeiro mensal por cliente.
    Mostra MRR, upgrades/downgrades e expansão de receita.
    Clientes que churnam frequentemente fazem downgrade antes de cancelar.
    """
    plan_order = ["starter", "growth", "pro", "enterprise"]
    rows = []
    today = date.today()
 
    for c in customers:
        cs = c["churn_score"]
        current_plan = c["plan"]
        current_plan_idx = plan_order.index(current_plan)
 
        for month_offset in range(c["tenure_months"]):
            month_date = c["acquisition_date"].replace(day=1) + timedelta(days=30 * month_offset)
            if month_date > today:
                break
 
            # Downgrade: clientes insatisfeitos tendem a fazer downgrade nos últimos meses
            is_last_months = month_offset >= c["tenure_months"] - 3
            if is_last_months and cs > 0.6 and current_plan_idx > 0:
                if random.random() < 0.3:
                    current_plan_idx -= 1
 
            plan_at_month = plan_order[current_plan_idx]
            mrr_at_month = PLANS[plan_at_month]["mrr"]
 
            rows.append({
                "financial_id":  fake.uuid4(),
                "customer_id":   c["customer_id"],
                "month":         month_date.isoformat()[:7],  # "YYYY-MM"
                "plan":          plan_at_month,
                "mrr_brl":       mrr_at_month,
                "expansion_brl": 0 if cs > 0.5 else random.choice([0, 0, 0, 150, 300]),
                "contraction_brl": random.choice([0, 100, 200]) if cs > 0.6 and is_last_months else 0,
                "churned_revenue_brl": mrr_at_month if (c["churned"] and is_last_months and month_offset == c["tenure_months"] - 1) else 0,
            })
 
    return pd.DataFrame(rows)
 
 
# ── Núcleo: gera os clientes base ──────────────────────────────────────────────
 
def generate_customers() -> list[dict]:
    """
    Cria a lista base de clientes com atributos latentes.
    O churn_score não vai para nenhum dataset — ele é apenas o
    gerador das correlações. O modelo de ML vai ter que descobri-las.
    """
    today = date.today()
    start_date = date(2022, 1, 1)
    customers = []
 
    for i in range(NUM_CUSTOMERS):
        plan = weighted_choice(PLANS)
        acquisition_date = random_date(start_date, today - timedelta(days=60))
 
        # churn_score: variável latente (0 = fiel, 1 = certeza de churn)
        churn_score = random.betavariate(1.5, 4)  # maioria tem score baixo (realista)
        churned = random.random() < churn_score
 
        if churned:
            min_tenure = 30
            max_tenure = (today - acquisition_date).days - 30
            if max_tenure < min_tenure:
                churned = False
                cancellation_date = None
                tenure_months = (today - acquisition_date).days // 30
            else:
                tenure_days = random.randint(min_tenure, max_tenure)
                cancellation_date = acquisition_date + timedelta(days=tenure_days)
                tenure_months = tenure_days // 30
        else:
            cancellation_date = None
            tenure_months = (today - acquisition_date).days // 30
 
        tenure_months = max(1, tenure_months)
 
        customers.append({
            "customer_id":       f"CUST-{i+1:05d}",
            "plan":              plan,
            "acquisition_date":  acquisition_date,
            "cancellation_date": cancellation_date,
            "churned":           churned,
            "tenure_months":     tenure_months,
            "churn_score":       round(churn_score, 4),  # só usado internamente
        })
 
    return customers
 
 
# ── Execução principal ─────────────────────────────────────────────────────────
 
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("🚀 Gerando dados fictícios...")
 
    customers = generate_customers()
    churned_count = sum(1 for c in customers if c["churned"])
    print(f"   Clientes gerados: {len(customers)}")
    print(f"   Churned: {churned_count} ({churned_count/len(customers)*100:.1f}%)")
 
    datasets = {
        "crm":         generate_crm(customers),
        "transactions": generate_transactions(customers),
        "support":     generate_support(customers),
        "engagement":  generate_engagement(customers),
        "financial":   generate_financial(customers),
    }
 
    for name, df in datasets.items():
        path = OUTPUT_DIR / f"{name}.parquet"
        df.to_parquet(path, index=False)
        print(f"   ✓ {name}.parquet  →  {len(df):,} linhas  |  {path.stat().st_size / 1024:.0f} KB")
 
    print("\nDados gerados em data/raw/")
 
 
if __name__ == "__main__":
    main()
