"""Pagina 7 - Mapa de Atuacao: Cooperativas por UF."""

import streamlit as st
import pandas as pd

from src.api.bcb import buscar_sedes_cooperativas, buscar_instituicoes_funcionamento
from src.utils.constants import CORES, TRANSPOCRED_NOME
from src.utils.formatting import formatar_numero
from src.components.kpi_card import kpi_row
from src.components.charts import grafico_mapa_brasil, grafico_barras

st.header("Mapa de Atuacao")
st.markdown("Distribuicao geografica das cooperativas de credito no Brasil.")

# === Carregar dados ===
df_sedes = buscar_sedes_cooperativas()

if not df_sedes.empty:
    # === Identificar colunas disponiveis ===
    col_uf = "UF" if "UF" in df_sedes.columns else None
    col_classe = None
    col_tipo = None
    col_categoria = None
    col_nome = None

    # Detectar colunas da BcBase v2
    for col in df_sedes.columns:
        col_lower = col.lower()
        if col_lower == "uf" and col_uf is None:
            col_uf = col
        if "classe" in col_lower and "cooperativa" in col_lower:
            col_classe = col
        if "tipo" in col_lower and "cooperativa" in col_lower:
            col_tipo = col
        if "categoria" in col_lower and "cooperativa" in col_lower:
            col_categoria = col
        if "nomeentidade" in col_lower or "razao" in col_lower:
            col_nome = col

    # Fallback para deteccao generica
    if col_uf is None:
        for col in df_sedes.columns:
            col_lower = col.lower()
            if "uf" in col_lower or "estado" in col_lower or "sigla" in col_lower:
                col_uf = col
                break
    if col_nome is None:
        for col in df_sedes.columns:
            if "nome" in col.lower():
                col_nome = col
                break

    # === Filtros ===
    st.sidebar.markdown("### Filtros do Mapa")
    df_filtrado = df_sedes.copy()

    if col_classe:
        classes = ["Todos"] + sorted(df_sedes[col_classe].dropna().unique().tolist())
        classe_sel = st.sidebar.selectbox("Classe", classes)
        if classe_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_classe] == classe_sel]

    if col_tipo:
        tipos = ["Todos"] + sorted(df_sedes[col_tipo].dropna().unique().tolist())
        tipo_sel = st.sidebar.selectbox("Tipo de Cooperativa", tipos)
        if tipo_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_tipo] == tipo_sel]

    if col_categoria:
        categorias = ["Todos"] + sorted(df_sedes[col_categoria].dropna().unique().tolist())
        cat_sel = st.sidebar.selectbox("Categoria", categorias)
        if cat_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_categoria] == cat_sel]

    # === KPIs ===
    total_coops = len(df_filtrado)
    kpis = [
        {"label": "Total de Cooperativas", "valor": formatar_numero(total_coops)},
    ]
    if col_uf:
        ufs_presentes = df_filtrado[col_uf].nunique()
        kpis.append({"label": "UFs com Cooperativas", "valor": formatar_numero(ufs_presentes)})
    kpi_row(kpis)

    st.markdown("---")

    # === Mapa ===
    if col_uf:
        df_por_uf = df_filtrado.groupby(col_uf).size().reset_index(name="Quantidade")

        col1, col2 = st.columns([2, 1])

        with col1:
            fig = grafico_mapa_brasil(
                df_por_uf, coluna_uf=col_uf, coluna_valor="Quantidade",
                titulo="Cooperativas de Credito por UF",
            )
            if fig:
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown(f"**Destaque:** {TRANSPOCRED_NOME} - Sede em **SC**")
            st.markdown("---")

            df_por_uf_sorted = df_por_uf.sort_values("Quantidade", ascending=False)
            st.dataframe(
                df_por_uf_sorted.rename(columns={col_uf: "UF"}),
                use_container_width=True,
                hide_index=True,
                height=400,
            )

        fig_barras = grafico_barras(
            df_por_uf.sort_values("Quantidade", ascending=False).head(15),
            x=col_uf, y="Quantidade",
            titulo="Top 15 UFs por Quantidade de Cooperativas",
            cor=CORES["verde_ailos"],
        )
        st.plotly_chart(fig_barras, use_container_width=True)
    else:
        st.warning("Coluna de UF nao identificada nos dados.")
        st.dataframe(df_filtrado.head(20), use_container_width=True)
else:
    # Fallback: tentar com instituicoes em funcionamento
    st.warning("Dados de cooperativas nao disponiveis. Tentando fonte alternativa...")

    df_inst = buscar_instituicoes_funcionamento()

    if not df_inst.empty:
        st.info(f"Carregadas {len(df_inst)} instituicoes. Filtrando cooperativas...")

        mask_coop = df_inst.apply(
            lambda row: any("cooperativa" in str(v).lower() for v in row.values), axis=1
        )
        df_coops = df_inst[mask_coop]

        if not df_coops.empty:
            st.metric("Cooperativas encontradas", formatar_numero(len(df_coops)))
            st.dataframe(df_coops.head(50), use_container_width=True)
        else:
            st.info("Nenhuma cooperativa encontrada com os filtros aplicados.")
    else:
        st.error("Nao foi possivel carregar dados de cooperativas de nenhuma fonte.")

st.markdown("---")
st.caption("Fonte: Banco Central do Brasil - BcBase v2 / Cadastro de Cooperativas")
