"""Pagina 1 - Visao Geral da Transpocred."""

import streamlit as st
import pandas as pd

from src.api.bcb import buscar_ifdata_transpocred, buscar_ifdata_evolucao
from src.utils.constants import TRANSPOCRED_CNPJ_8, TRANSPOCRED_NOME, IFDATA_RELATORIOS
from src.utils.formatting import formatar_bilhoes, formatar_numero, formatar_percentual
from src.components.kpi_card import kpi_row
from src.components.charts import grafico_linha, grafico_barras

st.header(f"Visao Geral - {TRANSPOCRED_NOME}")
st.markdown(
    "Principais indicadores da Transpocred - Cooperativa de Credito dos Trabalhadores "
    "em Transportes, Correios e Logistica (Sistema Ailos)."
)

# === Carregar dados ===
df_resumo = buscar_ifdata_transpocred(IFDATA_RELATORIOS["RESUMO"])
df_info = buscar_ifdata_transpocred(IFDATA_RELATORIOS["INFO_CAPITAL"])

# === Extrair KPIs do resumo ===
def extrair_valor(df, nome_conta):
    """Extrai valor de uma conta especifica do IF.data."""
    if df.empty:
        return None
    mask = df["NomeConta"].str.contains(nome_conta, case=False, na=False)
    resultado = df.loc[mask, "Valor"]
    if not resultado.empty:
        return resultado.iloc[0]
    return None

ativo_total = extrair_valor(df_resumo, "Ativo Total") if not df_resumo.empty else None
patrimonio_liq = extrair_valor(df_resumo, "Patrimonio Liquido") if not df_resumo.empty else None
depositos = extrair_valor(df_resumo, "Deposito Total") if not df_resumo.empty else None
op_credito = extrair_valor(df_resumo, "Operacoes de Credito") if not df_resumo.empty else None

# === KPI Cards ===
kpis = []
if ativo_total is not None:
    kpis.append({
        "label": "Ativo Total",
        "valor": formatar_bilhoes(ativo_total * 1000),
        "help": "Ativo total da cooperativa (IF.data)",
    })
if patrimonio_liq is not None:
    kpis.append({
        "label": "Patrimonio Liquido",
        "valor": formatar_bilhoes(patrimonio_liq * 1000),
        "help": "Patrimonio liquido da cooperativa",
    })
if op_credito is not None:
    kpis.append({
        "label": "Operacoes de Credito",
        "valor": formatar_bilhoes(op_credito * 1000),
        "help": "Saldo de operacoes de credito",
    })
if depositos is not None:
    kpis.append({
        "label": "Depositos Totais",
        "valor": formatar_bilhoes(depositos * 1000),
        "help": "Total de depositos captados",
    })

# KPIs fixos (dados institucionais publicos)
kpis.append({"label": "Cooperados", "valor": formatar_numero(58200), "help": "Numero aproximado de cooperados"})
kpis.append({"label": "Pontos de Atendimento", "valor": "51", "help": "Quantidade de pontos de atendimento"})

if kpis:
    kpi_row(kpis[:4])
    if len(kpis) > 4:
        kpi_row(kpis[4:])

st.markdown("---")

# === Evolucao Trimestral ===
st.subheader("Evolucao Trimestral")

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
            titulo="Evolucao do Ativo Total (R$ mil)",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Filtrar PL
    df_pl = df_evolucao[
        df_evolucao["NomeConta"].str.contains("Patrimonio Liquido", case=False, na=False)
    ].copy()
    if not df_pl.empty:
        df_pl = df_pl.sort_values("DataBase")
        df_pl["Trimestre"] = df_pl["DataBase"].apply(
            lambda x: f"{x[:4]}T{int(x[4:])//3}" if len(str(x)) >= 6 else x
        )
        fig = grafico_barras(
            df_pl, x="Trimestre", y="Valor",
            titulo="Evolucao do Patrimonio Liquido (R$ mil)",
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Dados de evolucao trimestral nao disponiveis no momento.")

# === Informacoes cadastrais ===
if not df_info.empty:
    st.markdown("---")
    st.subheader("Informacoes Cadastrais")
    st.dataframe(
        df_info[["NomeConta", "Valor"]].rename(columns={"NomeConta": "Informacao", "Valor": "Detalhe"}),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")
st.caption("Fonte: Banco Central do Brasil - IF.data (Relatorios 1 e 5)")
