"""
DAG: bronze_ingestion
Descrição: Orquestra a ingestão de todos os silos na camada Bronze.

Cronograma: diário às 02:00 UTC
Fluxo:
    start
      ├── ingest_crm
      ├── ingest_transactions
      ├── ingest_support
      ├── ingest_engagement
      └── ingest_financial
            └── end
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator

from ingestion.operators.bronze_operator import BronzeIngestionOperator

RAW_PATH = PROJECT_ROOT / "data" / "raw"
BRONZE_PATH = PROJECT_ROOT / "data" / "bronze"

SILOS = {
    "crm":          "crm.parquet",
    "transactions": "transactions.parquet",
    "support":      "support.parquet",
    "engagement":   "engagement.parquet",
    "financial":    "financial.parquet",
}

DEFAULT_ARGS = {
    "owner":            "data-engineering",
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": False,
}

def ingest_silo(source_name, source_file, **context):
    execution_date = context.get("ds", "manual")
    print(f"\n[{execution_date}] Ingerindo silo: {source_name}")
    operator = BronzeIngestionOperator(
        source_name=source_name,
        source_path=RAW_PATH / source_file,
        bronze_base_path=BRONZE_PATH,
        mode="append",
    )
    return operator.run()

with DAG(
    dag_id="bronze_ingestion",
    description="Ingestão diaria de todos os silos na camada Bronze",
    schedule_interval="0 2 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["bronze", "ingestion","lakehouse"],
    default_args=DEFAULT_ARGS,
) as dag:
    
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    ingest_tasks = []
    for silo_name, silo_file in SILOS.items():
        task = PythonOperator(
            task_id=f"ingest_{silo_name}",
            python_callable=ingest_silo,
            op_kwargs={
                "source_name": silo_name,
                "source_file": silo_file,
            },
        )
        ingest_tasks.append(task)
    
    start >> ingest_tasks >> end
