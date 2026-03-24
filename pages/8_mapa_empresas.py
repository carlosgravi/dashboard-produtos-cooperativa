"""Página 8 - Mapa de Empresas de Transporte, Logística e Correios.

Dois modos:
- Overview: mapa Folium com CircleMarker por município (dados agregados)
- Detail: mapa Folium com MarkerCluster por empresa individual (quando UF tem dados)
"""

import math

import folium
import pandas as pd
import streamlit as st
from folium.plugins import MarkerCluster, FastMarkerCluster
from streamlit_folium import st_folium

from src.api.empresas import (
    carregar_resumo_por_municipio,
    carregar_resumo_por_uf,
    resumo_empresas_por_categoria,
    filtrar_municipios,
    listar_ufs_com_dados_individuais,
    carregar_empresas_uf,
    filtrar_empresas_individuais,
)
from src.utils.constants import CORES, CATEGORIAS_EMPRESAS, CORES_CATEGORIAS_MAPA
from src.utils.formatting import formatar_numero
from src.components.kpi_card import kpi_row
from src.components.charts import grafico_barras, grafico_pizza

st.header("Mapa de Empresas de Transporte, Logística e Correios")
st.markdown("Geolocalização de empresas do setor no Brasil por CNAE (Receita Federal).")

# === Carregar dados ===
df_municipios = carregar_resumo_por_municipio()
df_uf = carregar_resumo_por_uf()
df_categorias = resumo_empresas_por_categoria()
ufs_individuais = listar_ufs_com_dados_individuais()

if df_municipios.empty and df_uf.empty:
    st.warning(
        "Dados de empresas não disponíveis. Execute os scripts de coleta:\n\n"
        "```bash\n"
        "pip install basedosdados\n"
        "python scripts/buscar_empresas_transporte.py\n"
        "python scripts/geocodificar_ceps.py\n"
        "```"
    )
    st.stop()

# === Sidebar - Filtros ===
st.sidebar.markdown("### Filtros")

categorias_opcoes = ["Todas"] + list(CATEGORIAS_EMPRESAS.keys())
categoria_sel = st.sidebar.selectbox("Categoria", categorias_opcoes)

ufs_disponiveis = ["Todas"]
if not df_uf.empty and "uf" in df_uf.columns:
    ufs_disponiveis += sorted(df_uf["uf"].unique().tolist())
uf_sel = st.sidebar.selectbox("UF", ufs_disponiveis)

fonte_sel = "Todas"
if not df_uf.empty and "fonte_rntrc" in df_uf.columns and df_uf["fonte_rntrc"].sum() > 0:
    fonte_sel = st.sidebar.selectbox("Fonte", ["Todas", "RFB", "RNTRC"])

# Info sobre UFs com dados individuais
if ufs_individuais:
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**UFs com dados individuais:** {', '.join(ufs_individuais)}")
    st.sidebar.caption("Selecione uma dessas UFs para ver empresas individuais no mapa.")

# Determinar modo: detail (UF com dados individuais) ou overview
modo_detail = uf_sel != "Todas" and uf_sel in ufs_individuais

# === Aplicar filtros nos dados agregados ===
df_mun_filtrado = filtrar_municipios(df_municipios, categoria=categoria_sel, uf=uf_sel, fonte=fonte_sel)

df_uf_filtrado = df_uf.copy() if not df_uf.empty else pd.DataFrame()
if not df_uf_filtrado.empty and uf_sel != "Todas":
    df_uf_filtrado = df_uf_filtrado[df_uf_filtrado["uf"] == uf_sel]

# === KPIs ===
total_empresas = int(df_mun_filtrado["total"].sum()) if not df_mun_filtrado.empty and "total" in df_mun_filtrado.columns else 0
ufs_presentes = df_mun_filtrado["uf"].nunique() if not df_mun_filtrado.empty and "uf" in df_mun_filtrado.columns else 0

top_uf = "—"
if not df_uf_filtrado.empty and "total" in df_uf_filtrado.columns:
    top_row = df_uf_filtrado.sort_values("total", ascending=False).iloc[0]
    top_uf = f"{top_row['uf']} ({formatar_numero(top_row['total'])})"

top_cat = "—"
if not df_categorias.empty:
    top_cat_row = df_categorias.iloc[0]
    top_cat = top_cat_row["categoria"]

kpis = [
    {"label": "Total de Empresas", "valor": formatar_numero(total_empresas)},
    {"label": "UFs Presentes", "valor": formatar_numero(ufs_presentes)},
    {"label": "Top UF", "valor": top_uf},
    {"label": "Top Categoria", "valor": top_cat},
]
kpi_row(kpis)

st.markdown("---")

# ============================================================
# MODO DETAIL: Mapa individual com MarkerCluster
# ============================================================

if modo_detail:
    df_empresas = carregar_empresas_uf(uf_sel)

    if df_empresas.empty:
        st.warning(f"Arquivo de empresas individuais para {uf_sel} está vazio.")
        st.stop()

    # Filtros adicionais para modo detail
    col_filtros = st.columns([1, 1, 2])

    with col_filtros[0]:
        municipios_disponiveis = ["Todos"] + sorted(df_empresas["municipio"].dropna().unique().tolist())
        municipio_sel = st.selectbox("Município", municipios_disponiveis)

    with col_filtros[1]:
        max_marcadores = st.slider("Máx. marcadores no mapa", 1000, 50000, 10000, step=1000)

    with col_filtros[2]:
        busca_texto = st.text_input("Buscar (nome, CNPJ ou endereço)", "")

    # Aplicar filtros
    df_detail = filtrar_empresas_individuais(
        df_empresas,
        categoria=categoria_sel,
        municipio=municipio_sel,
        busca=busca_texto,
    )

    st.markdown(f"**{formatar_numero(len(df_detail))} empresas** encontradas em {uf_sel}")

    # === Mapa + Tabela ===
    col_mapa, col_tabela = st.columns([2, 1])

    with col_mapa:
        # Filtrar apenas empresas com coordenadas
        df_com_geo = df_detail.copy()
        if "lat" in df_com_geo.columns and "lon" in df_com_geo.columns:
            df_com_geo["lat"] = pd.to_numeric(df_com_geo["lat"], errors="coerce")
            df_com_geo["lon"] = pd.to_numeric(df_com_geo["lon"], errors="coerce")
            df_com_geo = df_com_geo.dropna(subset=["lat", "lon"])

        if not df_com_geo.empty:
            # Limitar marcadores
            df_mapa = df_com_geo.head(max_marcadores)

            # Centro do mapa
            lat_center = df_mapa["lat"].mean()
            lon_center = df_mapa["lon"].mean()

            m = folium.Map(
                location=[lat_center, lon_center],
                zoom_start=7,
                tiles="CartoDB positron",
            )

            # Usar FastMarkerCluster para >20K pontos
            if len(df_mapa) > 20000:
                callback = """\
                function (row) {
                    var marker = L.marker(new L.LatLng(row[0], row[1]));
                    marker.bindPopup(row[2]);
                    return marker;
                }"""
                data = []
                for _, row in df_mapa.iterrows():
                    popup = (
                        f"<b>{row.get('nome', '—')}</b><br>"
                        f"CNPJ: {row.get('cnpj', '—')}<br>"
                        f"CNAE: {row.get('cnae_desc', '—')}<br>"
                        f"End: {row.get('endereco', '—')}<br>"
                        f"CEP: {row.get('cep', '—')}<br>"
                        f"Fonte: {row.get('fonte', '—')}"
                    )
                    data.append([row["lat"], row["lon"], popup])
                FastMarkerCluster(data=data, callback=callback).add_to(m)
            else:
                marker_cluster = MarkerCluster().add_to(m)
                for _, row in df_mapa.iterrows():
                    cat = row.get("categoria", "Outros")
                    cor = CORES_CATEGORIAS_MAPA.get(cat, "gray")
                    popup_html = (
                        f"<b>{row.get('nome', '—')}</b><br>"
                        f"CNPJ: {row.get('cnpj', '—')}<br>"
                        f"CNAE: {row.get('cnae_desc', '—')}<br>"
                        f"End: {row.get('endereco', '—')}<br>"
                        f"CEP: {row.get('cep', '—')}<br>"
                        f"Fonte: {row.get('fonte', '—')}"
                    )
                    folium.Marker(
                        location=[row["lat"], row["lon"]],
                        popup=folium.Popup(popup_html, max_width=300),
                        icon=folium.Icon(color=cor, icon="info-sign"),
                    ).add_to(marker_cluster)

            if len(df_com_geo) > max_marcadores:
                st.caption(f"Exibindo {formatar_numero(max_marcadores)} de {formatar_numero(len(df_com_geo))} empresas com coordenadas. Ajuste o slider para ver mais.")

            st_folium(m, use_container_width=True, height=550)
        else:
            st.info(
                f"Nenhuma empresa com coordenadas em {uf_sel}. Execute a geocodificação:\n\n"
                f"```bash\npython scripts/geocodificar_ceps.py --uf {uf_sel}\n```"
            )

    with col_tabela:
        st.markdown("**Empresas por UF**")
        if not df_uf_filtrado.empty and "total" in df_uf_filtrado.columns:
            df_tab = df_uf_filtrado[["uf", "total"]].sort_values("total", ascending=False).copy()
            df_tab.columns = ["UF", "Total"]
            st.dataframe(df_tab, use_container_width=True, hide_index=True, height=500)
        else:
            st.info("Dados por UF não disponíveis.")

    st.markdown("---")

    # === Tabela de empresas individuais ===
    st.subheader(f"Empresas em {uf_sel}")

    colunas_exibir = ["nome", "cnpj", "categoria", "endereco", "cep", "municipio", "fonte"]
    colunas_exibir = [c for c in colunas_exibir if c in df_detail.columns]
    df_exibir = df_detail[colunas_exibir].copy()

    renames = {
        "nome": "Nome",
        "cnpj": "CNPJ",
        "categoria": "Categoria",
        "endereco": "Endereço",
        "cep": "CEP",
        "municipio": "Município",
        "fonte": "Fonte",
    }
    df_exibir = df_exibir.rename(columns=renames)

    st.dataframe(df_exibir, use_container_width=True, hide_index=True, height=400)

# ============================================================
# MODO OVERVIEW: Mapa agregado com CircleMarker
# ============================================================

else:
    col_mapa, col_tabela = st.columns([2, 1])

    with col_mapa:
        df_com_geo = df_mun_filtrado.copy()
        if "lat" in df_com_geo.columns and "lon" in df_com_geo.columns:
            df_com_geo["lat"] = pd.to_numeric(df_com_geo["lat"], errors="coerce")
            df_com_geo["lon"] = pd.to_numeric(df_com_geo["lon"], errors="coerce")
            df_com_geo = df_com_geo.dropna(subset=["lat", "lon"])

        if not df_com_geo.empty:
            col_tamanho = "total_filtrado" if "total_filtrado" in df_com_geo.columns else "total"

            # Centro do Brasil
            lat_center = -14.2
            lon_center = -51.9
            zoom = 4

            # Se filtrado por UF, centralizar na UF
            if uf_sel != "Todas":
                lat_center = df_com_geo["lat"].mean()
                lon_center = df_com_geo["lon"].mean()
                zoom = 6

            m = folium.Map(
                location=[lat_center, lon_center],
                zoom_start=zoom,
                tiles="CartoDB positron",
            )

            # Calcular raio proporcional
            max_val = df_com_geo[col_tamanho].max()
            min_radius = 3
            max_radius = 25

            for _, row in df_com_geo.iterrows():
                val = row[col_tamanho]
                if val <= 0:
                    continue

                # Raio proporcional (escala log)
                ratio = math.log1p(val) / math.log1p(max_val) if max_val > 0 else 0
                radius = min_radius + ratio * (max_radius - min_radius)

                mun_label = row.get("municipio", "")
                uf_label = row.get("uf", "")
                popup_text = f"<b>{mun_label} - {uf_label}</b><br>Total: {int(val)}"

                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=radius,
                    popup=folium.Popup(popup_text, max_width=250),
                    color=CORES["verde_ailos"],
                    fill=True,
                    fill_color=CORES["verde_ailos"],
                    fill_opacity=0.6,
                    weight=1,
                ).add_to(m)

            st_folium(m, use_container_width=True, height=550)
        else:
            st.info(
                "Mapa indisponível. Execute a geocodificação:\n\n"
                "```bash\npython scripts/geocodificar_ceps.py\n```"
            )

    with col_tabela:
        st.markdown("**Empresas por UF**")
        if not df_uf_filtrado.empty and "total" in df_uf_filtrado.columns:
            df_tab = df_uf_filtrado[["uf", "total"]].sort_values("total", ascending=False).copy()
            df_tab.columns = ["UF", "Total"]
            st.dataframe(df_tab, use_container_width=True, hide_index=True, height=500)
        else:
            st.info("Dados por UF não disponíveis.")

    st.markdown("---")

    # === Gráficos: Barras Top UFs + Pizza Categorias ===
    col_barras, col_pizza = st.columns(2)

    with col_barras:
        if not df_uf.empty and "total" in df_uf.columns:
            df_top = df_uf.sort_values("total", ascending=False).head(15).copy()
            fig_barras = grafico_barras(
                df_top, x="uf", y="total",
                titulo="Top 15 UFs por Quantidade de Empresas",
                cor=CORES["verde_ailos"],
            )
            st.plotly_chart(fig_barras, use_container_width=True)

    with col_pizza:
        if not df_categorias.empty:
            fig_pizza = grafico_pizza(
                df_categorias, valores="total", nomes="categoria",
                titulo="Distribuição por Categoria",
            )
            st.plotly_chart(fig_pizza, use_container_width=True)

    # === Tabela completa ===
    with st.expander("Tabela completa por município"):
        if not df_mun_filtrado.empty:
            colunas_exibir = ["municipio", "uf", "total"]
            colunas_exibir = [c for c in colunas_exibir if c in df_mun_filtrado.columns]

            for cat in CATEGORIAS_EMPRESAS:
                col_cat = cat.lower().replace(" ", "_").replace("ã", "a").replace("í", "i")
                if col_cat in df_mun_filtrado.columns:
                    colunas_exibir.append(col_cat)

            df_exibir = df_mun_filtrado[colunas_exibir].sort_values("total", ascending=False)

            renames = {
                "municipio": "Município",
                "uf": "UF",
                "total": "Total",
            }
            for cat in CATEGORIAS_EMPRESAS:
                col_cat = cat.lower().replace(" ", "_").replace("ã", "a").replace("í", "i")
                if col_cat in df_exibir.columns:
                    renames[col_cat] = cat

            df_exibir = df_exibir.rename(columns=renames)

            busca = st.text_input("Buscar município", "")
            if busca:
                df_exibir = df_exibir[
                    df_exibir["Município"].astype(str).str.contains(busca, case=False, na=False)
                ]

            st.dataframe(df_exibir, use_container_width=True, hide_index=True, height=400)
        else:
            st.info("Sem dados para exibir.")

st.markdown("---")
st.caption("Fontes: Receita Federal / CNPJ (Base dos Dados / BigQuery) | Geocodificação: Nominatim (OSM), AwesomeAPI, IBGE")
