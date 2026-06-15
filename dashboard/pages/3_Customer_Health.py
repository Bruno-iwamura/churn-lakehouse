import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Customer Health", page_icon="🎯", layout="wide")

conn  = st.session_state.get("conn")
query = st.session_state.get("query")

if not conn:
    st.error("Conexão não inicializada. Acesse a página principal primeiro.")
    st.stop()

with st.spinner("Carregando health dos clientes..."):
    df = query(conn, "SELECT * FROM churn_lakehouse.semantic.sem_customer_health ORDER BY churn_probability DESC")

st.title("🎯 Customer Health")
st.caption("Health score e ações recomendadas por cliente")
st.divider()

# ── Filtros ────────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    segment_filter = st.multiselect(
        "Segmento de risco",
        options=["high", "medium", "low"],
        default=["high"],
    )
with col2:
    plan_filter = st.multiselect(
        "Plano",
        options=df["plan"].unique().tolist(),
        default=df["plan"].unique().tolist(),
    )
with col3:
    min_mrr = st.slider(
        "MRR mínimo (R$)",
        min_value=0,
        max_value=int(df["current_mrr_brl"].max()),
        value=0,
        step=100,
    )

# Aplica filtros
df_filtered = df[
    (df["risk_segment"].isin(segment_filter)) &
    (df["plan"].isin(plan_filter)) &
    (df["current_mrr_brl"] >= min_mrr)
]

st.divider()

# ── Métricas do filtro atual ───────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Clientes filtrados",     f"{len(df_filtered):,}")
c2.metric("MRR em risco",           f"R$ {df_filtered['individual_mrr_at_risk'].sum():,.0f}")
c3.metric("Health score médio",     f"{df_filtered['health_score'].mean():.1f}")
c4.metric("Prob. churn média",      f"{df_filtered['churn_probability'].mean():.1%}")

st.divider()

# ── Gráficos ───────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Distribuição de Health Score")
    fig1 = px.histogram(
        df_filtered,
        x="health_score",
        nbins=20,
        color="risk_segment",
        color_discrete_map={"high": "#ef4444", "medium": "#f97316", "low": "#22c55e"},
        labels={"health_score": "Health Score", "risk_segment": "Risco"},
    )
    fig1.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("MRR em Risco por Segmento")
    fig2 = px.box(
        df_filtered,
        x="risk_segment",
        y="individual_mrr_at_risk",
        color="risk_segment",
        color_discrete_map={"high": "#ef4444", "medium": "#f97316", "low": "#22c55e"},
        labels={"individual_mrr_at_risk": "MRR em Risco (R$)", "risk_segment": "Risco"},
    )
    fig2.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

# ── Tabela de clientes ─────────────────────────────────────────────────────────
st.subheader(f"Clientes — {len(df_filtered):,} registros")

st.dataframe(
    df_filtered[[
        "company_name", "plan", "industry", "tenure_months",
        "current_mrr_brl", "health_score", "risk_segment",
        "churn_probability", "individual_mrr_at_risk",
        "top_churn_reason", "recommended_action",
    ]].rename(columns={
        "company_name":          "Empresa",
        "plan":                  "Plano",
        "industry":              "Indústria",
        "tenure_months":         "Tenure (meses)",
        "current_mrr_brl":       "MRR (R$)",
        "health_score":          "Health Score",
        "risk_segment":          "Risco",
        "churn_probability":     "Prob. Churn",
        "individual_mrr_at_risk":"MRR em Risco (R$)",
        "top_churn_reason":      "Principal Razão",
        "recommended_action":    "Ação Recomendada",
    }),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Prob. Churn": st.column_config.ProgressColumn(
            "Prob. Churn",
            min_value=0,
            max_value=1,
            format="%.1%",
        ),
        "Health Score": st.column_config.ProgressColumn(
            "Health Score",
            min_value=0,
            max_value=100,
            format="%.0f",
        ),
    },
)
