"""
Exporta as tabelas Silver do DuckDB para o Neon PostgreSQL.
"""

from pathlib import Path
import duckdb
import pandas as pd
from sqlalchemy import create_engine, text
import psycopg2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRONZE_PATH  = PROJECT_ROOT / "data" / "bronze"
DUCKDB_PATH  = PROJECT_ROOT / "data" / "silver" / "churn_silver.duckdb"

NEON_URL = "postgresql://neondb_owner:npg_olG6y7PVjqYd@ep-nameless-dust-acz29w5z-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

MATERIALIZED = [
    "int_customer_transactions",
    "int_customer_financial",
    "int_customer_360",
]

STAGING_QUERIES = {
    "stg_crm": f"""
        SELECT
            customer_id,
            company_name,
            industry,
            plan,
            acquisition_date::date      AS acquisition_date,
            cancellation_date::date     AS cancellation_date,
            churned::boolean            AS churned,
            city,
            state,
            employees_range,
            CASE WHEN churned
                 THEN datediff('day', acquisition_date::date, cancellation_date::date)
                 ELSE datediff('day', acquisition_date::date, current_date)
            END                         AS tenure_days
        FROM (
            SELECT *, row_number() OVER (PARTITION BY customer_id ORDER BY _ingested_at DESC) AS rn
            FROM read_parquet('{BRONZE_PATH}/crm/**/*.parquet')
        ) WHERE rn = 1 AND customer_id IS NOT NULL
    """,
    "stg_support": f"""
        SELECT
            support_id,
            customer_id,
            nps_score::int              AS nps_score,
            nps_category,
            total_tickets::int          AS total_tickets,
            open_tickets::int           AS open_tickets,
            avg_resolution_hours::double AS avg_resolution_hours,
            last_ticket_type,
            CASE WHEN total_tickets > 0
                 THEN round(open_tickets::double / total_tickets, 4)
                 ELSE 0
            END                         AS open_ticket_rate
        FROM (
            SELECT *, row_number() OVER (PARTITION BY customer_id ORDER BY _ingested_at DESC) AS rn
            FROM read_parquet('{BRONZE_PATH}/support/**/*.parquet')
        ) WHERE rn = 1 AND customer_id IS NOT NULL
    """,
    "stg_engagement": f"""
        SELECT
            engagement_id,
            customer_id,
            period_days::int            AS period_days,
            total_logins_90d::int       AS total_logins_90d,
            avg_logins_per_week::double AS avg_logins_per_week,
            active_features::int        AS active_features,
            feature_list,
            last_login_days_ago::int    AS last_login_days_ago,
            api_calls_30d::int          AS api_calls_30d,
            users_active_30d::int       AS users_active_30d,
            CASE WHEN avg_logins_per_week >= 3 THEN 'high'
                 WHEN avg_logins_per_week >= 1 THEN 'medium'
                 ELSE 'low'
            END                         AS engagement_level
        FROM (
            SELECT *, row_number() OVER (PARTITION BY customer_id ORDER BY _ingested_at DESC) AS rn
            FROM read_parquet('{BRONZE_PATH}/engagement/**/*.parquet')
        ) WHERE rn = 1 AND customer_id IS NOT NULL
    """,
    "stg_transactions": f"""
        SELECT
            transaction_id,
            customer_id,
            invoice_date::date          AS invoice_date,
            due_date::date              AS due_date,
            paid_date::date             AS paid_date,
            amount_brl::double          AS amount_brl,
            amount_paid_brl::double     AS amount_paid_brl,
            days_late::int              AS days_late,
            status,
            discount_pct::int           AS discount_pct,
            (days_late > 0)             AS is_late,
            (days_late > 30)            AS is_severely_late,
            (amount_brl - amount_paid_brl) AS amount_unpaid_brl
        FROM (
            SELECT *, row_number() OVER (PARTITION BY transaction_id ORDER BY _ingested_at DESC) AS rn
            FROM read_parquet('{BRONZE_PATH}/transactions/**/*.parquet')
        ) WHERE rn = 1 AND customer_id IS NOT NULL AND amount_brl > 0
    """,
    "stg_financial": f"""
        SELECT
            financial_id,
            customer_id,
            month,
            plan,
            mrr_brl::double             AS mrr_brl,
            expansion_brl::double       AS expansion_brl,
            contraction_brl::double     AS contraction_brl,
            churned_revenue_brl::double AS churned_revenue_brl,
            (mrr_brl + expansion_brl - contraction_brl) AS net_mrr_brl
        FROM (
            SELECT *, row_number() OVER (PARTITION BY financial_id ORDER BY _ingested_at DESC) AS rn
            FROM read_parquet('{BRONZE_PATH}/financial/**/*.parquet')
        ) WHERE rn = 1 AND customer_id IS NOT NULL AND mrr_brl > 0
    """,
}


def get_pg_conn(engine):
    url = engine.url
    return psycopg2.connect(
        host=url.host,
        port=url.port or 5432,
        database=url.database,
        user=url.username,
        password=url.password,
        sslmode="require",
    )


def write_df(df: pd.DataFrame, table: str, engine) -> None:
    conn = get_pg_conn(engine)
    cursor = conn.cursor()

    cursor.execute(f'DROP TABLE IF EXISTS silver."{table}"')

    cols = []
    for col, dtype in df.dtypes.items():
        if "int" in str(dtype):
            pg_type = "BIGINT"
        elif "float" in str(dtype) or "double" in str(dtype):
            pg_type = "DOUBLE PRECISION"
        elif "bool" in str(dtype):
            pg_type = "BOOLEAN"
        elif "date" in str(dtype):
            pg_type = "DATE"
        else:
            pg_type = "TEXT"
        cols.append(f'"{col}" {pg_type}')

    cursor.execute(f'CREATE TABLE silver."{table}" ({", ".join(cols)})')

    records = [
        tuple(None if (v is not None and pd.isna(v)) else v for v in row)
        for row in df.itertuples(index=False)
    ]
    placeholders = "(" + ",".join(["%s"] * len(df.columns)) + ")"
    col_names = ", ".join([f'"{c}"' for c in df.columns])

    batch_size = 2000
    for i in range(0, len(records), batch_size):
        cursor.executemany(
            f'INSERT INTO silver."{table}" ({col_names}) VALUES {placeholders}',
            records[i:i+batch_size]
        )

    conn.commit()
    cursor.close()
    conn.close()


def export_to_neon():
    print(f"\n{'='*55}")
    print("  Silver → Neon PostgreSQL")
    print(f"{'='*55}")

    con = duckdb.connect(str(DUCKDB_PATH))
    engine = create_engine(NEON_URL)

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS silver"))
    print("  Schema 'silver' verificado\n")

    total_rows = 0

    for table in MATERIALIZED:
        try:
            df = con.execute(f"SELECT * FROM main.{table}").df()
            write_df(df, table, engine)
            print(f"  ✓ {table:<30} {len(df):>8,} linhas")
            total_rows += len(df)
        except Exception as e:
            print(f"  ✗ {table:<30} ERRO: {e}")

    for table, query in STAGING_QUERIES.items():
        try:
            df = con.execute(query).df()
            write_df(df, table, engine)
            print(f"  ✓ {table:<30} {len(df):>8,} linhas")
            total_rows += len(df)
        except Exception as e:
            print(f"  ✗ {table:<30} ERRO: {e}")

    con.close()
    print(f"\n{'─'*55}")
    print(f"  Total exportado: {total_rows:,} linhas")
    print(f"  Destino: Neon → schema 'silver'\n")


if __name__ == "__main__":
    export_to_neon()
