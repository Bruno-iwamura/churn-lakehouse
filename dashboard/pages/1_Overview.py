import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")

conn  = st.session_state.get("conn")
query = st.session_state.get("query")

if not conn:
    st.error("Conexão não inicializada. Acesse a página principal primeiro.")
    st.stop()

# ── Carrega dados ──────────────────────────────────────────────────────────────
with st.spinner("Carregando métricas..."):
    df_overview = query(conn, "SELECT * FROM churn_lakehouse.semantic.sem_churn_overview")
    df_risk     = query(conn, "SELECT * FROM churn_lakehouse.semantic.sem_revenue_at_risk")

row = df_overview.iloc[0]

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("📊 Executive Overview")
st.caption("Visão consolidada de churn e receita em risco")
st.divider()

# ── Cards de métricas ──────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

c1.metric(
    label="MRR Ativo Total",
    value=f"R$ {row['total_active_mrr']:,.0f}",
    delta=None,
)
c2.metric(
    label="MRR em Risco",
    value=f"R$ {row['expected_mrr_loss']:,.0f}",
    delta=f"{row['expected_mrr_loss']/row['total_active_mrr']*100:.1f}% do MRR total",
    delta_color="inverse",
)
c3.metric(
    label="Clientes Alto Risco",
    value=f"{int(row['high_risk_customers']):,}",
    delta=f"de {int(row['total_active']):,} ativos",
    delta_color="inverse",
)
c4.metric(
    label="Churn Rate Previsto",
    value=f"{row['predicted_churn_rate_pct']:.1f}%",
    delta=f"histórico: {row['churn_rate_pct']:.1f}%",
    delta_color="off",
)

st.divider()

# ── Gráficos ───────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("MRR em Risco por Plano")
    fig1 = px.bar(
        df_risk,
        x="plan",
        y="expected_mrr_loss",
        color="risk_segment",
        barmode="group",
        color_discrete_map={"high": "#ef4444", "medium": "#f97316", "low": "#22c55e"},
        labels={"expected_mrr_loss": "MRR em Risco (R$)", "plan": "Plano", "risk_segment": "Risco"},
        text_auto=".2s",
    )
    fig1.update_layout(height=380, plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("Distribuição de Clientes por Risco")
    risk_data = {
        "Segmento": ["Alto Risco", "Médio Risco", "Baixo Risco"],
        "Clientes": [
            int(row["high_risk_customers"]),
            int(row["medium_risk_customers"]),
            int(row["low_risk_customers"]),
        ]
    }
    fig2 = px.pie(
        risk_data,
        names="Segmento",
        values="Clientes",
        hole=0.5,
        color="Segmento",
        color_discrete_map={
            "Alto Risco":  "#ef4444",
            "Médio Risco": "#f97316",
            "Baixo Risco": "#22c55e",
        },
    )
    fig2.update_layout(height=380)
    st.plotly_chart(fig2, use_container_width=True)

# ── Tabela de MRR por plano e risco ───────────────────────────────────────────
st.subheader("MRR em Risco — Detalhamento por Plano e Segmento")
st.dataframe(
    df_risk.rename(columns={
        "plan":              "Plano",
        "risk_segment":      "Segmento",
        "customers":         "Clientes",
        "total_mrr":         "MRR Total (R$)",
        "expected_mrr_loss": "MRR em Risco (R$)",
        "avg_churn_prob_pct":"Prob. Churn Média (%)",
        "mrr_at_risk_pct":   "% MRR em Risco",
    }),
    use_container_width=True,
    hide_index=True,
)
