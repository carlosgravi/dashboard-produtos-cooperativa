"""Pagina 3 - Panorama do Cooperativismo de Credito."""

import streamlit as st
from datetime import datetime, timedelta

from src.api.bcb import buscar_serie_sgs
from src.utils.constants import SGS, CORES
from src.utils.formatting import formatar_numero, formatar_bilhoes
from src.components.kpi_card import kpi_row
from src.components.charts import grafico_linha, grafico_linhas_multiplas

st.header("Panorama do Cooperativismo de Credito")
st.markdown("Evolucao do setor cooperativista de credito no Brasil com dados do Banco Central.")

# === Periodo ===
data_inicio = (datetime.now() - timedelta(days=365 * 5)).strftime("%d/%m/%Y")
data_fim = datetime.now().strftime("%d/%m/%Y")

# === Carregar dados ===
df_qtd = buscar_serie_sgs(SGS["COOP_QTD"], data_inicio, data_fim)
df_cred_pf = buscar_serie_sgs(SGS["COOP_CREDITO_PF"], data_inicio, data_fim)
df_cred_pj = buscar_serie_sgs(SGS["COOP_CREDITO_PJ"], data_inicio, data_fim)
df_dep_pf = buscar_serie_sgs(SGS["COOP_DEPOSITOS_PF"], data_inicio, data_fim)
df_central = buscar_serie_sgs(SGS["COOP_CENTRAL"], data_inicio, data_fim)
df_singular = buscar_serie_sgs(SGS["COOP_SINGULAR"], data_inicio, data_fim)

# === KPIs ===
kpis = []
if not df_qtd.empty:
    kpis.append({
        "label": "Cooperativas de Credito",
        "valor": formatar_numero(df_qtd["valor"].iloc[-1]),
        "help": "Quantidade de cooperativas de credito em funcionamento",
    })
if not df_cred_pf.empty:
    kpis.append({
        "label": "Credito PF (Cooperativas)",
        "valor": formatar_bilhoes(df_cred_pf["valor"].iloc[-1] * 1e6),
        "help": "Saldo de operacoes de credito PF em cooperativas (R$ milhoes)",
    })
if not df_cred_pj.empty:
    kpis.append({
        "label": "Credito PJ (Cooperativas)",
        "valor": formatar_bilhoes(df_cred_pj["valor"].iloc[-1] * 1e6),
        "help": "Saldo de operacoes de credito PJ em cooperativas (R$ milhoes)",
    })
if not df_dep_pf.empty:
    kpis.append({
        "label": "Depositos PF (Cooperativas)",
        "valor": formatar_bilhoes(df_dep_pf["valor"].iloc[-1] * 1e6),
        "help": "Depositos a vista PF em cooperativas (R$ milhoes)",
    })

if kpis:
    kpi_row(kpis)

st.markdown("---")

# === Graficos ===
col1, col2 = st.columns(2)

with col1:
    if not df_qtd.empty:
        fig = grafico_linha(
            df_qtd, x="data", y="valor",
            titulo="Evolucao da Quantidade de Cooperativas",
            cor=CORES["verde_ailos"],
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Dados de quantidade de cooperativas nao disponiveis.")

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
        st.info("Dados de cooperativas centrais/singulares nao disponiveis.")

st.markdown("### Saldo de Credito em Cooperativas")
col3, col4 = st.columns(2)

with col3:
    if not df_cred_pf.empty:
        fig = grafico_linha(
            df_cred_pf, x="data", y="valor",
            titulo="Credito PF - Cooperativas (R$ milhoes)",
            cor=CORES["azul"],
        )
        st.plotly_chart(fig, use_container_width=True)

with col4:
    if not df_cred_pj.empty:
        fig = grafico_linha(
            df_cred_pj, x="data", y="valor",
            titulo="Credito PJ - Cooperativas (R$ milhoes)",
            cor=CORES["laranja"],
        )
        st.plotly_chart(fig, use_container_width=True)

if not df_dep_pf.empty:
    st.markdown("### Depositos a Vista PF em Cooperativas")
    fig = grafico_linha(
        df_dep_pf, x="data", y="valor",
        titulo="Depositos a Vista PF (R$ milhoes)",
        cor=CORES["verde_escuro"],
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("Fonte: Banco Central do Brasil - SGS (Series 24869, 25517, 25518, 25519, 25509, 25510)")
