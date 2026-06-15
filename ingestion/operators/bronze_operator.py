"""
Operador reutilizável para ingestão na camada Bronze.

Responsabilidades:
  1. Ler o arquivo raw de uma fonte (Parquet, CSV ou JSON)
  2. Adicionar metadados de ingestão em cada linha
  3. Gravar no Data Lake em formato Delta, particionado por data
"""

from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from deltalake import DeltaTable, write_deltalake

class BronzeIngestionOperator:
    def __init__(self, source_name, source_path, bronze_base_path, mode="append"):
        self.source_name = source_name
        self.source_path = Path(source_path)
        self.bronze_base_path = Path(bronze_base_path)
        self.mode = mode
        self.target_path = self.bronze_base_path / source_name

    def _read_source(self):
        suffix = self.source_path.suffix.lower()
        readers = {".parquet": pd.read_parquet, ".csv": pd.read_csv, ".json": pd.read_json}
        if not suffix in readers:
            raise ValueError(f"Unsupported file format: {suffix}")
        df = readers[suffix](self.source_path)
        print(f"Lidos {len(df):,} registros de {self.source_path.name}")
        return df
    
    def _add_metadata(self, df):
        now = datetime.now(timezone.utc)
        df = df.copy()
        df["_ingested_at"] = now.isoformat()
        df["_ingestion_date"] = now.date().isoformat()
        df["_source_name"] = self.source_name
        df["_source_file"] = self.source_path.name
        df["_pipeline_version"] = "1.0.0"
        return df
    
    def _validate(self, df):
        if df.empty:
            raise ValueError(f"Fonte {self.source_name} retornou DataFrame vazio.")
        if "customer_id" not in df.columns:
            raise ValueError(f"Coluna 'customer_id' ausente em {self.source_name}.")
        null_pct = df["customer_id"].isna().mean()
        if null_pct > 0.10:
            raise ValueError(f"customer_id tem {null_pct:.1%} de nulos em {self.source_name}.")
        print(f"   Validação OK — {len(df):,} registros, {len(df.columns)} colunas")

    def _write_delta(self, df):
        self.target_path.mkdir(parents=True, exist_ok=True)
        write_deltalake(
            str(self.target_path),
            df,
            mode=self.mode,
            partition_by=["_ingestion_date"],
            schema_mode="merge",
        )
        dt = DeltaTable(str(self.target_path))
        history = dt.history(limit=1)[0]
        print(f"   Delta gravado em: {self.target_path}")
        print(f"   Versão da tabela: {history.get('version', 'n/a')}")
        print(f"   Operação:         {history.get('operation', 'n/a')}")

    def run(self):
        print(f"\n── Iniciando ingestão Bronze: {self.source_name} ──")
        started_at = datetime.now(timezone.utc)
        df = self._read_source()
        self._validate(df)
        df = self._add_metadata(df)
        self._write_delta(df)
        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        print(f"── Ingestão Bronze concluída em {elapsed:.2f} segundos")
        return {
            "source": self.source_name,
            "rows": len(df),
            "columns": len(df.columns),
            "elapsed_s": round(elapsed, 2),
            "status": "success",
        }

        