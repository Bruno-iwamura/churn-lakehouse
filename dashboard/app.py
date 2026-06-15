"""
Churn Lakehouse — Dashboard Executivo
Conecta nas views semânticas do Databricks e exibe métricas de churn.
"""

import streamlit as st
from databricks import sql

# ── Configuração da página ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Churn Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Conexão com Databricks ─────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    """
    Cria uma conexão reutilizável com o Databricks SQL Warehouse.
    @st.cache_resource garante que a conexão é criada uma vez
    e reutilizada em todas as páginas — sem reconectar a cada interação.
    """
    return sql.connect(
        server_hostname = st.secrets["databricks"]["server_hostname"],
        http_path       = st.secrets["databricks"]["http_path"],
        access_token    = st.secrets["databricks"]["access_token"],
    )

@st.cache_data(ttl=300)
def query(_conn, sql_query: str):
    """
    Executa uma query e retorna um DataFrame pandas.
    @st.cache_data com ttl=300 cacheia o resultado por 5 minutos —
    evita reprocessar a mesma query a cada interação do usuário.
    """
    import pandas as pd
    with _conn.cursor() as cursor:
        cursor.execute(sql_query)
        return cursor.fetchall_arrow().to_pandas()

# Disponibiliza conexão e função de query para todas as páginas
conn = get_connection()
st.session_state["conn"]  = conn
st.session_state["query"] = query

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/6/63/Databricks_Logo.png", width=140)
    st.title("Churn Analytics")
    st.caption("Powered by Databricks + MLflow")
    st.divider()
    st.markdown("""
    **Navegação**
    - 📊 Overview executivo
    - 📈 Análise por cohort
    - 🎯 Health dos clientes
    """)
    st.divider()
    st.caption("Dados atualizados a cada 5 minutos")

# ── Página inicial ─────────────────────────────────────────────────────────────
st.title("📊 Churn Analytics — Executive Dashboard")
st.markdown("Selecione uma página no menu lateral para começar.")
