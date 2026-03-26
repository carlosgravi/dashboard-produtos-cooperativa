"""Página 1 - Visão Geral da Transpocred."""

import streamlit as st
import pandas as pd

from src.api.bcb import buscar_ifdata_transpocred, buscar_ifdata_evolucao
from src.utils.constants import TRANSPOCRED_CNPJ_8, TRANSPOCRED_NOME, IFDATA_RELATORIOS
from src.utils.formatting import formatar_bilhoes, formatar_numero, formatar_percentual
from src.components.kpi_card import kpi_row
from src.components.charts import grafico_linha, grafico_barras

st.header(f"Visão Geral - {TRANSPOCRED_NOME}")
st.markdown(
    "Principais indicadores da Transpocred - Cooperativa de Crédito dos Trabalhadores "
    "em Transportes, Correios e Logística (Sistema Ailos)."
)

# === Carregar dados ===
df_resumo = buscar_ifdata_transpocred(IFDATA_RELATORIOS["RESUMO"])
df_info = buscar_ifdata_transpocred(IFDATA_RELATORIOS["INFO_CAPITAL"])

# === Extrair KPIs do resumo ===
def extrair_valor(df, nome_conta):
    """Extrai valor de uma conta específica do IF.data."""
    if df.empty:
        return None
    mask = df["NomeConta"].str.contains(nome_conta, case=False, na=False)
    resultado = df.loc[mask, "Valor"]
    if not resultado.empty:
        return resultado.iloc[0]
    return None

ativo_total = extrair_valor(df_resumo, "Ativo Total") if not df_resumo.empty else None
patrimonio_liq = extrair_valor(df_resumo, "nio L") if not df_resumo.empty else None
depositos = extrair_valor(df_resumo, "Capta") if not df_resumo.empty else None
op_credito = extrair_valor(df_resumo, "Carteira de Cr") if not df_resumo.empty else None

# === KPI Cards ===
kpis = []
if ativo_total is not None:
    kpis.append({
        "label": "Ativo Total",
        "valor": formatar_bilhoes(ativo_total ),
        "help": "Ativo total da cooperativa (IF.data)",
    })
if patrimonio_liq is not None:
    kpis.append({
        "label": "Patrimônio Líquido",
        "valor": formatar_bilhoes(patrimonio_liq ),
        "help": "Patrimônio líquido da cooperativa",
    })
if op_credito is not None:
    kpis.append({
        "label": "Operações de Crédito",
        "valor": formatar_bilhoes(op_credito ),
        "help": "Saldo de operações de crédito",
    })
if depositos is not None:
    kpis.append({
        "label": "Depósitos Totais",
        "valor": formatar_bilhoes(depositos ),
        "help": "Total de depósitos captados",
    })

# KPIs fixos (dados institucionais públicos)
kpis.append({"label": "Cooperados", "valor": formatar_numero(58200), "help": "Número aproximado de cooperados"})
kpis.append({"label": "Pontos de Atendimento", "valor": "51", "help": "Quantidade de pontos de atendimento"})

if kpis:
    kpi_row(kpis[:4])
    if len(kpis) > 4:
        kpi_row(kpis[4:])

st.markdown("---")

# === Evolução Trimestral ===
st.subheader("Evolução Trimestral")

df_evolucao = buscar_ifdata_evolucao(
    IFDATA_RELATORIOS["RESUMO"],
    cnpj_8=TRANSPOCRED_CNPJ_8,
    n_trimestres=12,
)

if not df_evolucao.empty:
    # Filtrar Ativo Total
    df_ativo = df_evolucao[
        df_evolucao["NomeConta"].str.contains("Ativo Total", case=False, na=False)
    ].copy()

    if not df_ativo.empty:
        df_ativo = df_ativo.sort_values("DataBase")
        df_ativo["Trimestre"] = df_ativo["DataBase"].apply(
            lambda x: f"{x[:4]}T{int(x[4:])//3}" if len(str(x)) >= 6 else x
        )
        fig = grafico_barras(
            df_ativo, x="Trimestre", y="Valor",
            titulo="Evolução do Ativo Total (R$)",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Filtrar PL
    df_pl = df_evolucao[
        df_evolucao["NomeConta"].str.contains("nio L", case=False, na=False)
    ].copy()
    if not df_pl.empty:
        df_pl = df_pl.sort_values("DataBase")
        df_pl["Trimestre"] = df_pl["DataBase"].apply(
            lambda x: f"{x[:4]}T{int(x[4:])//3}" if len(str(x)) >= 6 else x
        )
        fig = grafico_barras(
            df_pl, x="Trimestre", y="Valor",
            titulo="Evolução do Patrimônio Líquido (R$)",
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Dados de evolução trimestral não disponíveis no momento.")

# === Informações cadastrais ===
if not df_info.empty:
    st.markdown("---")
    st.subheader("Informações Cadastrais")
    st.dataframe(
        df_info[["NomeConta", "Valor"]].rename(columns={"NomeConta": "Informação", "Valor": "Detalhe"}),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")
with st.expander("Sobre os dados"):
    st.markdown("""
**Fonte dos dados:** Banco Central do Brasil — IF.data (Sistema de Informações de Instituições Financeiras)

**API utilizada:** OLINDA/BCB — Relatórios 1 (Resumo) e 5 (Informações de Capital)

**Principais métricas:**
- Ativo Total, Patrimônio Líquido, Operações de Crédito, Depósitos Totais
- Capital Social, Índice de Basileia
- Evolução trimestral (últimos 12 trimestres)

**Periodicidade:** Trimestral (último trimestre disponível)

**Atualização do dashboard:** Semanal (GitHub Actions) ou manual via `scripts/atualizar_dados.py`.
""")
