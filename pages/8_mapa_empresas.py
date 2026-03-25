"""Pagina 8 - Mapa de Empresas de Transporte, Logistica e Correios.

Mapa Folium com MarkerCluster por empresa individual, filtrado por UF.
"""

import folium
import pandas as pd
import streamlit as st
from folium.plugins import MarkerCluster, FastMarkerCluster
from streamlit_folium import st_folium

from src.api.empresas import (
    listar_ufs_com_dados_individuais,
    carregar_empresas_uf,
    filtrar_empresas_avancado,
)
from src.utils.constants import CORES, CATEGORIAS_EMPRESAS, CORES_CATEGORIAS_MAPA
from src.utils.formatting import formatar_numero
from src.components.kpi_card import kpi_row

st.header("Mapa de Empresas de Transporte, Logistica e Correios")
st.markdown("Geolocalizacao de empresas do setor por CNAE (Receita Federal).")

# === Verificar dados ===
ufs_individuais = listar_ufs_com_dados_individuais()

if not ufs_individuais:
    st.warning(
        "Nenhuma UF com dados individuais. Execute:\n\n"
        "```bash\n"
        "python scripts/buscar_empresas_transporte.py <PROJECT_ID> --uf SC\n"
        "```"
    )
    st.stop()

# === Sidebar - Filtros ===
st.sidebar.markdown("### Filtros")

idx_default = ufs_individuais.index("SC") if "SC" in ufs_individuais else 0
uf_sel = st.sidebar.selectbox("UF", ufs_individuais, index=idx_default)

categorias_opcoes = ["Todas"] + list(CATEGORIAS_EMPRESAS.keys())
categoria_sel = st.sidebar.selectbox("Categoria", categorias_opcoes)

# === Carregar dados da UF ===
df_empresas = carregar_empresas_uf(uf_sel)

if df_empresas.empty:
    st.warning(f"Arquivo de empresas individuais para {uf_sel} esta vazio.")
    st.stop()

# === Filtros inline ===
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    municipios_disponiveis = ["Todos"] + sorted(df_empresas["municipio"].dropna().unique().tolist())
    municipio_sel = st.selectbox("Municipio", municipios_disponiveis)

with col_f2:
    portes_disponiveis = sorted(df_empresas["porte_desc"].dropna().unique().tolist()) if "porte_desc" in df_empresas.columns else []
    porte_sel = st.multiselect("Porte", portes_disponiveis) if portes_disponiveis else []

with col_f3:
    busca_texto = st.text_input("Buscar (nome, CNPJ ou endereco)", "")

col_c1, col_c2, col_c3 = st.columns(3)

with col_c1:
    capital_min = st.number_input("Capital Social min (R$)", min_value=0, value=0, step=10000)

with col_c2:
    capital_max = st.number_input("Capital Social max (R$)", min_value=0, value=0, step=10000, help="0 = sem limite")

with col_c3:
    max_marcadores = st.slider("Max. marcadores no mapa", 500, 50000, 3000, step=500)

# === Aplicar filtros ===
df_detail = filtrar_empresas_avancado(
    df_empresas,
    categoria=categoria_sel,
    municipio=municipio_sel,
    porte=porte_sel if porte_sel else None,
    capital_min=capital_min if capital_min > 0 else None,
    capital_max=capital_max if capital_max > 0 else None,
    busca=busca_texto,
)

# === KPIs ===
total = len(df_detail)
total_uf = len(df_empresas)
capital_medio = df_detail["capital_social"].astype(float).mean() if total > 0 and "capital_social" in df_detail.columns else 0

kpis = [
    {"label": "Empresas filtradas", "valor": formatar_numero(total)},
    {"label": f"Total em {uf_sel}", "valor": formatar_numero(total_uf)},
]
if "porte_desc" in df_detail.columns and total > 0:
    maior_porte = df_detail["porte_desc"].value_counts().index[0]
    kpis.append({"label": "Porte predominante", "valor": maior_porte})
kpis.append({"label": "Capital social medio", "valor": f"R$ {capital_medio:,.0f}".replace(",", ".")})

kpi_row(kpis)
st.markdown("---")

st.markdown(f"**{formatar_numero(total)} empresas** encontradas em {uf_sel}")

# === Mapa + Tabela lateral ===
col_mapa, col_tabela = st.columns([2, 1])

with col_mapa:
    df_com_geo = df_detail.copy()
    if "lat" in df_com_geo.columns and "lon" in df_com_geo.columns:
        df_com_geo["lat"] = pd.to_numeric(df_com_geo["lat"], errors="coerce")
        df_com_geo["lon"] = pd.to_numeric(df_com_geo["lon"], errors="coerce")
        df_com_geo = df_com_geo.dropna(subset=["lat", "lon"])

    if not df_com_geo.empty:
        df_mapa = df_com_geo.head(max_marcadores)

        lat_center = df_mapa["lat"].mean()
        lon_center = df_mapa["lon"].mean()

        m = folium.Map(
            location=[lat_center, lon_center],
            zoom_start=7,
            tiles="CartoDB positron",
        )

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
                    f"<b>{row.get('nome', '')}</b><br>"
                    f"CNPJ: {row.get('cnpj', '')}<br>"
                    f"CNAE: {row.get('cnae_desc', '')}<br>"
                    f"End: {row.get('endereco', '')}<br>"
                    f"Porte: {row.get('porte_desc', '')}<br>"
                    f"Capital: R$ {row.get('capital_social', 0):,.0f}".replace(",", ".")
                )
                data.append([row["lat"], row["lon"], popup])
            FastMarkerCluster(data=data, callback=callback).add_to(m)
        else:
            marker_cluster = MarkerCluster().add_to(m)
            for _, row in df_mapa.iterrows():
                cat = row.get("categoria", "Outros")
                cor = CORES_CATEGORIAS_MAPA.get(cat, "gray")
                popup_html = (
                    f"<b>{row.get('nome', '')}</b><br>"
                    f"CNPJ: {row.get('cnpj', '')}<br>"
                    f"CNAE: {row.get('cnae_desc', '')}<br>"
                    f"End: {row.get('endereco', '')}<br>"
                    f"Porte: {row.get('porte_desc', '')}<br>"
                    f"Capital: R$ {row.get('capital_social', 0):,.0f}".replace(",", ".")
                )
                folium.Marker(
                    location=[row["lat"], row["lon"]],
                    popup=folium.Popup(popup_html, max_width=300),
                    icon=folium.Icon(color=cor, icon="info-sign"),
                ).add_to(marker_cluster)

        if len(df_com_geo) > max_marcadores:
            st.caption(f"Exibindo {formatar_numero(max_marcadores)} de {formatar_numero(len(df_com_geo))} empresas com coordenadas.")

        st_folium(m, use_container_width=True, height=550)
    else:
        st.info(
            f"Nenhuma empresa com coordenadas em {uf_sel}. Execute a geocodificacao:\n\n"
            f"```bash\npython scripts/geocodificar_ceps.py --uf {uf_sel}\n```"
        )

with col_tabela:
    st.markdown("**Distribuicao por categoria**")
    if "categoria" in df_detail.columns and total > 0:
        cat_counts = df_detail["categoria"].value_counts().reset_index()
        cat_counts.columns = ["Categoria", "Total"]
        st.dataframe(cat_counts, use_container_width=True, hide_index=True, height=250)

    st.markdown("**Distribuicao por porte**")
    if "porte_desc" in df_detail.columns and total > 0:
        porte_counts = df_detail["porte_desc"].value_counts().reset_index()
        porte_counts.columns = ["Porte", "Total"]
        st.dataframe(porte_counts, use_container_width=True, hide_index=True, height=200)

st.markdown("---")

# === Tabela de empresas ===
st.subheader(f"Empresas em {uf_sel}")

colunas_exibir = ["nome", "cnpj", "categoria", "porte_desc", "nat_juridica_desc",
                   "capital_social", "telefone", "email", "endereco", "cep", "municipio"]
colunas_exibir = [c for c in colunas_exibir if c in df_detail.columns]
df_exibir = df_detail[colunas_exibir].copy()

renames = {
    "nome": "Nome",
    "cnpj": "CNPJ",
    "categoria": "Categoria",
    "porte_desc": "Porte",
    "nat_juridica_desc": "Nat. Juridica",
    "capital_social": "Capital Social",
    "telefone": "Telefone",
    "email": "Email",
    "endereco": "Endereco",
    "cep": "CEP",
    "municipio": "Municipio",
}
df_exibir = df_exibir.rename(columns=renames)

st.dataframe(df_exibir, use_container_width=True, hide_index=True, height=400)

st.markdown("---")
st.caption("Fontes: Receita Federal / CNPJ (Base dos Dados / BigQuery) | Geocodificacao: Nominatim (OSM), AwesomeAPI, IBGE")
