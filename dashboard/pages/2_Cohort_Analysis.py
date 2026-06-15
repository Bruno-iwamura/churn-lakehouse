import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Cohort Analysis", page_icon="📈", layout="wide")

conn  = st.session_state.get("conn")
query = st.session_state.get("query")

if not conn:
    st.error("Conexão não inicializada. Acesse a página principal primeiro.")
    st.stop()

with st.spinner("Carregando análise de cohorts..."):
    df = query(conn, "SELECT * FROM churn_lakehouse.semantic.sem_cohort_analysis ORDER BY acquisition_cohort")

st.title("📈 Análise por Cohort de Aquisição")
st.caption("Comportamento de churn por trimestre de aquisição")
st.divider()

# ── Métricas do cohort mais recente ───────────────────────────────────────────
latest = df.iloc[-1]
oldest = df.iloc[0]

c1, c2, c3 = st.columns(3)
c1.metric("Cohorts analisados",  f"{len(df)}")
c2.metric("Churn rate médio",    f"{df['churn_rate_pct'].mean():.1f}%")
c3.metric("MRR total em risco",  f"R$ {df['expected_mrr_loss'].sum():,.0f}")

st.divider()

# ── Churn rate por cohort ──────────────────────────────────────────────────────
st.subheader("Churn Rate por Cohort")
fig1 = px.line(
    df,
    x="acquisition_cohort",
    y="churn_rate_pct",
    markers=True,
    labels={"churn_rate_pct": "Churn Rate (%)", "acquisition_cohort": "Cohort"},
    color_discrete_sequence=["#6366f1"],
)
fig1.add_hline(
    y=df["churn_rate_pct"].mean(),
    line_dash="dash",
    line_color="#ef4444",
    annotation_text=f"Média: {df['churn_rate_pct'].mean():.1f}%",
)
fig1.update_layout(height=350, plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig1, use_container_width=True)

# ── MRR Total vs MRR em Risco ─────────────────────────────────────────────────
st.subheader("MRR Total vs MRR em Risco por Cohort")
fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=df["acquisition_cohort"],
    y=df["total_mrr"],
    name="MRR Total",
    marker_color="#6366f1",
))
fig2.add_trace(go.Bar(
    x=df["acquisition_cohort"],
    y=df["expected_mrr_loss"],
    name="MRR em Risco",
    marker_color="#ef4444",
))
fig2.update_layout(
    barmode="overlay",
    height=350,
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis_title="Cohort",
    yaxis_title="R$",
)
st.plotly_chart(fig2, use_container_width=True)

# ── Tabela detalhada ───────────────────────────────────────────────────────────
st.subheader("Detalhamento por Cohort")
st.dataframe(
    df.rename(columns={
        "acquisition_cohort":      "Cohort",
        "total_customers":         "Clientes",
        "churned_customers":       "Churned",
        "churn_rate_pct":          "Churn Rate (%)",
        "avg_tenure_days":         "Tenure Médio (dias)",
        "avg_predicted_churn_pct": "Churn Previsto (%)",
        "total_mrr":               "MRR Total (R$)",
        "expected_mrr_loss":       "MRR em Risco (R$)",
    }),
    use_container_width=True,
    hide_index=True,
)
