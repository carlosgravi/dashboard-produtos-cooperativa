"""Página 5 - Indicadores Econômicos: Selic, CDI, IPCA, IGP-M, Dólar."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from src.api.bcb import buscar_serie_sgs
from src.utils.constants import SGS, CORES
from src.utils.formatting import formatar_percentual, formatar_moeda
from src.components.kpi_card import kpi_row
from src.components.charts import grafico_linha, grafico_linhas_multiplas, grafico_barras

st.header("Indicadores Econômicos")
st.markdown("Acompanhamento dos principais indicadores macroeconômicos do Brasil.")

# === Seletor de período ===
col_periodo1, col_periodo2 = st.columns(2)
with col_periodo1:
    anos_atras = st.selectbox(
        "Período",
        options=[1, 2, 3, 5, 10],
        index=1,
        format_func=lambda x: f"Últimos {x} ano{'s' if x > 1 else ''}",
    )
with col_periodo2:
    st.markdown("")  # spacer

data_inicio = (datetime.now() - timedelta(days=365 * anos_atras)).strftime("%d/%m/%Y")
data_fim = datetime.now().strftime("%d/%m/%Y")

# === Carregar dados ===
df_selic = buscar_serie_sgs(SGS["SELIC"], data_inicio, data_fim)
df_cdi = buscar_serie_sgs(SGS["CDI"], data_inicio, data_fim)
df_ipca = buscar_serie_sgs(SGS["IPCA"], data_inicio, data_fim)
df_igpm = buscar_serie_sgs(SGS["IGPM"], data_inicio, data_fim)
df_dolar = buscar_serie_sgs(SGS["DOLAR_PTAX"], data_inicio, data_fim)

# === KPIs ===
kpis = []
if not df_selic.empty:
    kpis.append({"label": "Selic (meta)", "valor": formatar_percentual(df_selic["valor"].iloc[-1]), "help": "Taxa Selic meta anualizada"})
if not df_cdi.empty:
    kpis.append({"label": "CDI", "valor": formatar_percentual(df_cdi["valor"].iloc[-1]), "help": "Taxa CDI anualizada"})
if not df_ipca.empty:
    ipca_12m = df_ipca["valor"].tail(12).sum() if len(df_ipca) >= 12 else df_ipca["valor"].sum()
    kpis.append({"label": "IPCA (12m)", "valor": formatar_percentual(ipca_12m), "help": "IPCA acumulado 12 meses"})
if not df_dolar.empty:
    kpis.append({"label": "Dólar (PTAX)", "valor": formatar_moeda(df_dolar["valor"].iloc[-1]), "help": "Cotação dólar PTAX venda"})

if kpis:
    kpi_row(kpis)

st.markdown("---")

# === Gráficos ===
tab1, tab2, tab3, tab4 = st.tabs(["Selic & CDI", "IPCA", "IGP-M", "Dólar"])

with tab1:
    if not df_selic.empty and not df_cdi.empty:
        df_juros = pd.merge(
            df_selic.rename(columns={"valor": "Selic"}),
            df_cdi.rename(columns={"valor": "CDI"}),
            on="data", how="outer"
        ).sort_values("data")
        fig = grafico_linhas_multiplas(
            df_juros, x="data", y_cols=["Selic", "CDI"],
            nomes=["Selic (meta)", "CDI"],
            titulo="Evolução Selic e CDI (% a.a.)",
            formato_y=",.2f",
        )
        st.plotly_chart(fig, use_container_width=True)
    elif not df_selic.empty:
        fig = grafico_linha(df_selic, x="data", y="valor", titulo="Evolução da Selic (% a.a.)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Dados de Selic/CDI não disponíveis.")

with tab2:
    if not df_ipca.empty:
        fig_ipca = grafico_barras(
            df_ipca, x="data", y="valor",
            titulo="IPCA Mensal (%)",
            cor=CORES["azul"],
        )
        st.plotly_chart(fig_ipca, use_container_width=True)

        # IPCA acumulado 12 meses
        df_ipca_ac = df_ipca.copy()
        df_ipca_ac["acumulado_12m"] = df_ipca_ac["valor"].rolling(window=12).sum()
        fig_ac = grafico_linha(
            df_ipca_ac.dropna(subset=["acumulado_12m"]),
            x="data", y="acumulado_12m",
            titulo="IPCA Acumulado 12 Meses (%)",
            cor=CORES["vermelho"],
        )
        st.plotly_chart(fig_ac, use_container_width=True)
    else:
        st.info("Dados do IPCA não disponíveis.")

with tab3:
    if not df_igpm.empty:
        fig_igpm = grafico_linha(
            df_igpm, x="data", y="valor",
            titulo="IGP-M Mensal (%)",
            cor=CORES["laranja"],
        )
        st.plotly_chart(fig_igpm, use_container_width=True)
    else:
        st.info("Dados do IGP-M não disponíveis.")

with tab4:
    if not df_dolar.empty:
        fig_dolar = grafico_linha(
            df_dolar, x="data", y="valor",
            titulo="Dólar PTAX (R$)",
            cor=CORES["azul_escuro"],
        )
        st.plotly_chart(fig_dolar, use_container_width=True)
    else:
        st.info("Dados do Dólar não disponíveis.")

st.markdown("---")
with st.expander("Sobre os dados"):
    st.markdown("""
**Fonte dos dados:** Banco Central do Brasil — SGS (Sistema Gerenciador de Séries Temporais)

**API utilizada:** SGS/BCB — Séries 4189 (Selic meta), 4391 (CDI), 433 (IPCA), 189 (IGP-M), 1 (Dólar PTAX venda)

**Principais métricas:**
- Taxa Selic meta (% a.a.)
- CDI (% a.a.)
- IPCA mensal e acumulado 12 meses
- IGP-M mensal
- Cotação do Dólar PTAX venda (R$)

**Periodicidade:** Diária (Selic, CDI, Dólar) / Mensal (IPCA, IGP-M)

**Atualização do dashboard:** Semanal (GitHub Actions) ou manual via `scripts/atualizar_dados.py`.
""")
