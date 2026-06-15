# Churn Lakehouse — End-to-End Data Engineering Portfolio

Dashboard executivo de predição de churn para uma empresa SaaS B2B fictícia,
demonstrando domínio completo do stack moderno de dados: da geração de dados
sintéticos até o modelo de ML em produção com explicabilidade.


## Arquitetura

Fontes (5 silos)

↓

Bronze Layer (Delta Lake + Apache Airflow)

↓

Silver Layer (dbt Core + DuckDB — 8 modelos, 20 testes)

↓

Neon PostgreSQL → Lakeflow Connect (CDC)

↓

Databricks Unity Catalog

↓

Gold Layer (PySpark — Customer 360 + Feature Store)

↓

ML (XGBoost + LightGBM + Stacking + SHAP + MLflow)

↓

Camada Semântica (SQL Views)

↓

Dashboard (Databricks AI/BI + Streamlit)

---

## Stack tecnológica

| Camada | Tecnologia |
|---|---|
| Geração de dados | Python + Faker |
| Orquestração | Apache Airflow |
| Storage | Delta Lake + Parquet |
| Transformação | dbt Core + DuckDB |
| Banco transacional | Neon PostgreSQL (serverless) |
| Replicação | Lakeflow Connect (CDC) |
| Plataforma cloud | Databricks Free Edition |
| Governança | Unity Catalog |
| ML | XGBoost, LightGBM, Stacking, SHAP, MLflow, Optuna |
| Dashboard | Databricks AI/BI + Streamlit |

---

## Resultados do modelo

| Modelo | ROC-AUC | PR-AUC |
|---|---|---|
| XGBoost baseline | 0.868 | 0.731 |
| XGBoost + features temporais | 0.934 | 0.847 |
| LightGBM + features temporais | 0.940 | 0.861 |
| **Stacking (LGBM + XGB + LR)** | **0.940** | **0.867** |

**Feature mais importante (SHAP):** `unpaid_last_3m` — valor não pago
nos últimos 3 meses é o sinal mais forte de churn iminente.

---

## Estrutura do repositório

churn-lakehouse/

├── ingestion/

│   ├── generators/       ← Gerador de dados sintéticos

│   ├── operators/        ← BronzeIngestionOperator

│   └── run_bronze.py     ← Runner local da camada Bronze

├── airflow/

│   └── dags/             ← DAG de ingestão Bronze

├── transform/

│   └── churn_silver/     ← Projeto dbt (Silver Layer)

│       ├── models/

│       │   ├── staging/  ← 5 modelos de limpeza

│       │   └── intermediate/ ← 3 modelos de joins

│       └── profiles.yml

├── databricks/           ← Notebooks Gold + ML + Semântica

├── dashboard/

│   ├── app.py            ← Streamlit principal

│   └── pages/            ← 3 páginas do dashboard

├── data/                 ← Gerado localmente (não versionado)

└── README.md

---

## Como rodar localmente

### Pré-requisitos
- Python 3.12+
- WSL2 (para o Airflow)
- Conta no Databricks Free Edition
- Conta no Neon PostgreSQL

### Setup

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/churn-lakehouse.git
cd churn-lakehouse

# 2. Crie o ambiente virtual
python -m venv .venv
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Gere os dados sintéticos
python ingestion/generators/generate_data.py

# 5. Ingestão Bronze
python ingestion/run_bronze.py

# 6. Transformação Silver (dbt)
cd transform/churn_silver
dbt run --profiles-dir .
dbt test --profiles-dir .
cd ../..

# 7. Configure as credenciais do Streamlit
cp dashboard/.streamlit/secrets.toml.example dashboard/.streamlit/secrets.toml
# Edite o arquivo com suas credenciais

# 8. Rode o dashboard
cd dashboard
streamlit run app.py

# 9. Dashboard Databricks

# Faça login em uma conta databricks
# Acesse: https://dbc-0b77dedc-bde6.cloud.databricks.com/dashboardsv3/01f165afa5341ff58ba1e6d88fcf9a6f/published/pages/customer_health?o=7474650620578095
```

---

## Decisões arquiteturais

**Por que Delta Lake?** Transações ACID, versionamento de dados e
compatibilidade nativa com o ecossistema Databricks/Spark.

**Por que dbt + DuckDB?** dbt organiza transformações SQL em projetos
versionáveis com testes e documentação. DuckDB elimina a necessidade
de um banco de dados local para desenvolvimento.

**Por que Neon + Lakeflow Connect?** Simula um cenário real de
replicação CDC de um banco transacional para o lakehouse, sem
depender de upload manual de arquivos.

**Por que Stacking?** Combina a diversidade de LightGBM, XGBoost e
Logistic Regression para um meta-learner mais robusto. O ganho foi
marginal nesse dataset (2k clientes) mas a técnica demonstra
conhecimento de ensemble methods.

**Por que SHAP?** Explicabilidade é requisito em ambientes de negócio
reais — Customer Success precisa saber *por que* um cliente está em
risco, não só *qual* é o risco.
