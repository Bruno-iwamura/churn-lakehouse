"""
Runner local da camada Bronze.

Executa o mesmo pipeline dos DAGs do Airflow sem precisar
subir o servidor. Use para desenvolvimento e testes.

Uso:
    python ingestion/run_bronze.py
    python ingestion/run_bronze.py --silo crm
    python ingestion/run_bronze.py --mode overwrite
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.operators.bronze_operator import BronzeIngestionOperator

RAW_PATH = PROJECT_ROOT / "data" / "raw"
BRONZE_PATH = PROJECT_ROOT / "data" / "bronze"

SILOS = {
    "crm": "crm.parquet",
    "transactions": "transactions.parquet",
    "support": "support.parquet",
    "engagement": "engagement.parquet",
    "financial": "financial.parquet",
}

def run(silo_filter=None, mode="append"):
    silos = (
        {k: v for k, v in SILOS.items() if k == silo_filter}
        if silo_filter else SILOS
    )

    if not silos:
        print(f"Silo '{silo_filter}' não encontrado. Opções: {list(SILOS.keys())}")
        sys.exit(1)
    
    print(f"\n{'='*55}")
    print(f"  Bronze Ingestion Runner  |  modo: {mode}")
    print(f"{'='*55}")

    results = []
    for name, file in silos.items():
        op = BronzeIngestionOperator(
            source_name=name,
            source_path=RAW_PATH / file,
            bronze_base_path=BRONZE_PATH,
            mode=mode,
        )
        result = op.run()
        results.append(result)

    print(f"\n{'='*55}")
    print("Resumo da ingestão:")
    print(f"{'='*55}")
    total_rows = 0

    for r in results:
        icon = "✓" if r["status"] == "success" else "✗"
        print(f"  {icon} {r['source']:<15} {r['rows']:>8,} linhas  ({r['elapsed_s']}s)")
        total_rows += r["rows"]
    print(f"{'─'*55}")
    print(f"  Total: {total_rows:,} registros ingeridos")
    print(f"  Bronze em: {BRONZE_PATH}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runner local da camada Bronze")
    parser.add_argument("--silo", help="Silo específico para rodar (ex: crm)")
    parser.add_argument("--mode", default="append", choices=["append", "overwrite"], help="Modo de escrita no Delta Lake")
    args = parser.parse_args()
    run(silo_filter=args.silo, mode=args.mode)