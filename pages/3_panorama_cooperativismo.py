"""Página 3 - Panorama do Cooperativismo de Crédito."""

import streamlit as st

from src.api.bcb import buscar_serie_sgs
from src.utils.constants import SGS, CORES
from src.utils.formatting import formatar_numero, formatar_bilhoes
from src.components.kpi_card import kpi_row
from src.components.charts import grafico_linha, grafico_linhas_multiplas

st.header("Panorama do Cooperativismo de Crédito")
st.markdown("Evolução do setor cooperativista de crédito no Brasil com dados do Banco Central.")

# === Carregar dados ===
# Séries de cooperativismo são anuais com dados históricos limitados (até 2018/2022).
# Carregar sem filtro de data para exibir todo o histórico disponível.
df_qtd = buscar_serie_sgs(SGS["COOP_QTD"])
df_cred_pf = buscar_serie_sgs(SGS["COOP_CREDITO_PF"])
df_cred_pj = buscar_serie_sgs(SGS["COOP_CREDITO_PJ"])
df_dep_pf = buscar_serie_sgs(SGS["COOP_DEPOSITOS_PF"])
df_central = buscar_serie_sgs(SGS["COOP_CENTRAL"])
df_singular = buscar_serie_sgs(SGS["COOP_SINGULAR"])

# === KPIs ===
kpis = []
if not df_qtd.empty:
    kpis.append({
        "label": "Cooperativas de Crédito",
        "valor": formatar_numero(df_qtd["valor"].iloc[-1]),
        "help": "Quantidade de cooperativas de crédito em funcionamento",
    })
if not df_cred_pf.empty:
    kpis.append({
        "label": "Crédito PF (Cooperativas)",
        "valor": formatar_bilhoes(df_cred_pf["valor"].iloc[-1] * 1e6),
        "help": "Saldo de operações de crédito PF em cooperativas (R$ milhões)",
    })
if not df_cred_pj.empty:
    kpis.append({
        "label": "Crédito PJ (Cooperativas)",
        "valor": formatar_bilhoes(df_cred_pj["valor"].iloc[-1] * 1e6),
        "help": "Saldo de operações de crédito PJ em cooperativas (R$ milhões)",
    })
if not df_dep_pf.empty:
    kpis.append({
        "label": "Depósitos PF (Cooperativas)",
        "valor": formatar_bilhoes(df_dep_pf["valor"].iloc[-1] * 1e6),
        "help": "Depósitos à vista PF em cooperativas (R$ milhões)",
    })

if kpis:
    kpi_row(kpis)

st.markdown("---")

# === Gráficos ===
col1, col2 = st.columns(2)

with col1:
    if not df_qtd.empty:
        fig = grafico_linha(
            df_qtd, x="data", y="valor",
            titulo="Evolução da Quantidade de Cooperativas",
            cor=CORES["verde_ailos"],
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Dados de quantidade de cooperativas não disponíveis.")

with col2:
    if not df_central.empty and not df_singular.empty:
        import pandas as pd
        df_tipo = pd.merge(
            df_central.rename(columns={"valor": "Centrais"}),
            df_singular.rename(columns={"valor": "Singulares"}),
            on="data", how="outer",
        ).sort_values("data")
        fig = grafico_linhas_multiplas(
            df_tipo, x="data", y_cols=["Centrais", "Singulares"],
            titulo="Cooperativas Centrais vs Singulares",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Dados de cooperativas centrais/singulares não disponíveis.")

st.markdown("### Saldo de Crédito em Cooperativas")
col3, col4 = st.columns(2)

with col3:
    if not df_cred_pf.empty:
        fig = grafico_linha(
            df_cred_pf, x="data", y="valor",
            titulo="Crédito PF - Cooperativas (R$ milhões)",
            cor=CORES["azul"],
        )
        st.plotly_chart(fig, use_container_width=True)

with col4:
    if not df_cred_pj.empty:
        fig = grafico_linha(
            df_cred_pj, x="data", y="valor",
            titulo="Crédito PJ - Cooperativas (R$ milhões)",
            cor=CORES["laranja"],
        )
        st.plotly_chart(fig, use_container_width=True)

if not df_dep_pf.empty:
    st.markdown("### Depósitos à Vista PF em Cooperativas")
    fig = grafico_linha(
        df_dep_pf, x="data", y="valor",
        titulo="Depósitos à Vista PF (R$ milhões)",
        cor=CORES["verde_escuro"],
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
with st.expander("Sobre os dados"):
    st.markdown("""
**Fonte dos dados:** Banco Central do Brasil — SGS (Sistema Gerenciador de Séries Temporais)

**API utilizada:** SGS/BCB — Séries 24869, 25509, 25510, 25517, 25518, 25519

**Principais métricas:**
- Quantidade de cooperativas de crédito em funcionamento
- Saldo de crédito PF e PJ em cooperativas (R$ milhões)
- Depósitos à vista PF em cooperativas
- Cooperativas centrais vs singulares

**Periodicidade:** Anual (séries históricas até 2018-2022)

**Atualização do dashboard:** Semanal (GitHub Actions) ou manual via `scripts/atualizar_dados.py`.
""")
