"""Página 6 - Setor de Transportes: RNTRC (ANTT) + Diesel (ANP)."""

import streamlit as st
import pandas as pd

from src.api.antt import (
    buscar_rntrc_veiculos,
    buscar_rntrc_transportadores_resumo,
    resumo_veiculos_por_uf,
    resumo_veiculos_por_tipo,
    resumo_idade_frota,
    resumo_transportadores_por_categoria,
)
from src.api.anp import (
    buscar_precos_diesel_recentes,
    calcular_preco_medio_diesel_por_uf,
    calcular_preco_medio_nacional,
)
from src.utils.constants import CORES
from src.utils.formatting import formatar_numero, formatar_moeda
from src.components.kpi_card import kpi_row
from src.components.charts import grafico_barras, grafico_pizza, grafico_mapa_brasil

st.header("Setor de Transportes")
st.markdown(
    "Panorama do transporte rodoviário de cargas no Brasil. "
    "**O diesel é o principal custo operacional do setor.**"
)

# === RNTRC ===
st.subheader("RNTRC - Registro Nacional de Transportadores")

tab_veiculos, tab_transportadores = st.tabs(["Frota de Veículos", "Transportadores"])

with tab_veiculos:
    df_veiculos = buscar_rntrc_veiculos()

    _veiculos_ok = (isinstance(df_veiculos, dict) and "por_uf" in df_veiculos) or (
        isinstance(df_veiculos, pd.DataFrame) and not df_veiculos.empty
    )
    if _veiculos_ok:
        total_veiculos = df_veiculos.get("total", 0) if isinstance(df_veiculos, dict) else len(df_veiculos)
        st.metric("Total de Veículos Registrados", formatar_numero(total_veiculos))

        col1, col2 = st.columns(2)

        with col1:
            # Top 10 UFs
            df_uf = resumo_veiculos_por_uf(df_veiculos)
            if not df_uf.empty:
                col_uf = "UF_Veiculo" if "UF_Veiculo" in df_uf.columns else "UF"
                fig = grafico_barras(
                    df_uf.head(10), x=col_uf, y="Total_Veiculos",
                    titulo="Top 10 UFs por Quantidade de Veículos",
                    cor=CORES["verde_ailos"],
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Tipo de veículo
            df_tipo = resumo_veiculos_por_tipo(df_veiculos)
            if not df_tipo.empty:
                fig = grafico_pizza(
                    df_tipo.head(8), valores="Total", nomes="Tipo_Veiculo",
                    titulo="Distribuição por Tipo de Veículo",
                )
                st.plotly_chart(fig, use_container_width=True)

        # Idade da frota
        df_idade = resumo_idade_frota(df_veiculos)
        if not df_idade.empty:
            fig = grafico_barras(
                df_idade, x="Faixa_Idade", y="Quantidade",
                titulo="Idade da Frota",
                cor=CORES["azul"],
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(
            "Não foi possível carregar os dados de veículos RNTRC. "
            "O arquivo CSV da ANTT pode estar temporariamente indisponível."
        )

with tab_transportadores:
    df_transportadores = buscar_rntrc_transportadores_resumo()

    if not df_transportadores.empty:
        total_transp = df_transportadores["Quantidade"].sum()
        st.metric("Total de Registros de Transportadores", formatar_numero(total_transp))

        # Por categoria (TAC, ETC, CTC)
        df_cat = resumo_transportadores_por_categoria(df_transportadores)
        if not df_cat.empty:
            col1, col2 = st.columns(2)
            with col1:
                fig = grafico_pizza(
                    df_cat, valores="Quantidade", nomes="Categoria",
                    titulo="Transportadores por Categoria",
                )
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.markdown("**Categorias RNTRC:**")
                st.markdown(
                    "- **TAC** - Transportador Autônomo de Cargas\n"
                    "- **ETC** - Empresa de Transporte de Cargas\n"
                    "- **CTC** - Cooperativa de Transporte de Cargas"
                )
                st.dataframe(
                    df_cat.rename(columns={"Categoria": "Tipo", "Quantidade": "Total"}),
                    use_container_width=True,
                    hide_index=True,
                )
    else:
        st.warning("Não foi possível carregar os dados de transportadores RNTRC.")

# === Diesel (ANP) ===
st.markdown("---")
st.subheader("Preço do Diesel")
st.markdown("Dados de preços de combustíveis da ANP (Agência Nacional do Petróleo).")

df_diesel = buscar_precos_diesel_recentes()

if not df_diesel.empty:
    preco_medio = calcular_preco_medio_nacional(df_diesel)
    if preco_medio is not None:
        st.metric(
            "Preço Médio Nacional do Diesel",
            formatar_moeda(preco_medio),
            help="Média dos preços de venda coletados pela ANP",
        )

    col1, col2 = st.columns(2)

    with col1:
        df_uf_diesel = calcular_preco_medio_diesel_por_uf(df_diesel)
        if not df_uf_diesel.empty:
            fig = grafico_barras(
                df_uf_diesel, x="UF", y="Preco_Medio",
                titulo="Preço Médio do Diesel por UF (R$)",
                cor=CORES["laranja"],
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if not df_uf_diesel.empty:
            fig_mapa = grafico_mapa_brasil(
                df_uf_diesel, coluna_uf="UF", coluna_valor="Preco_Medio",
                titulo="Mapa de Preços do Diesel por UF",
                color_scale="YlOrRd",
            )
            if fig_mapa:
                st.plotly_chart(fig_mapa, use_container_width=True)
else:
    st.warning(
        "Não foi possível carregar os dados de preços do diesel. "
        "Os arquivos da ANP podem estar temporariamente indisponíveis."
    )

st.markdown("---")
with st.expander("Sobre os dados"):
    st.markdown("""
**Fontes dos dados:**
- ANTT — Registro Nacional de Transportadores Rodoviários de Cargas (RNTRC)
- ANP — Sistema de Levantamento de Preços (SLP)

**APIs utilizadas:**
- ANTT dados abertos: CSV direto (veículos) + CKAN API (transportadores)
- ANP dados abertos: CSV de preços de combustíveis

**Principais métricas:**
- Frota de veículos: total, por tipo, por UF e idade da frota
- Transportadores por categoria: TAC (Autônomo), ETC (Empresa), CTC (Cooperativa)
- Preço médio do Diesel por UF e nacional

**Periodicidade:** ANTT: mensal | ANP: semanal (últimas 4 semanas)

**Atualização do dashboard:** Semanal (GitHub Actions) ou manual via `scripts/atualizar_dados.py`.
""")
