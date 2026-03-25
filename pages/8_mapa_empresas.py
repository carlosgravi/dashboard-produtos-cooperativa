"""Pagina 8 - Mapa de Empresas de Transporte, Logistica e Correios.

Mapa PyDeck (deck.gl/WebGL) com empresas individuais filtradas por UF.
"""

import pandas as pd
import pydeck as pdk
import streamlit as st

from src.api.empresas import (
    listar_ufs_com_dados_individuais,
    carregar_empresas_uf,
    filtrar_empresas_avancado,
)
from src.utils.constants import CATEGORIAS_EMPRESAS
from src.utils.formatting import formatar_numero
from src.components.kpi_card import kpi_row

# Cores por categoria (RGB)
CORES_CATEGORIA = {
    "Transporte de Cargas": [46, 134, 193],
    "Transporte de Passageiros": [231, 76, 60],
    "Logistica e Armazenagem": [39, 174, 96],
    "Correios e Encomendas": [243, 156, 18],
    "Outros": [149, 165, 166],
}

# Centros aproximados das UFs para zoom inicial
CENTROS_UF = {
    "SC": {"lat": -27.6, "lon": -50.3, "zoom": 6.5},
    "PR": {"lat": -24.9, "lon": -51.4, "zoom": 6.2},
    "RS": {"lat": -29.7, "lon": -53.5, "zoom": 5.8},
    "SP": {"lat": -22.5, "lon": -48.5, "zoom": 5.8},
}
DEFAULT_CENTER = {"lat": -27.6, "lon": -50.3, "zoom": 6}

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

col_c1, col_c2 = st.columns(2)

with col_c1:
    capital_min = st.number_input("Capital Social min (R$)", min_value=0, value=0, step=10000)

with col_c2:
    capital_max = st.number_input("Capital Social max (R$)", min_value=0, value=0, step=10000, help="0 = sem limite")

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

# === Mapa PyDeck ===
df_mapa = df_detail.copy()
if "lat" in df_mapa.columns and "lon" in df_mapa.columns:
    df_mapa["lat"] = pd.to_numeric(df_mapa["lat"], errors="coerce")
    df_mapa["lon"] = pd.to_numeric(df_mapa["lon"], errors="coerce")
    df_mapa = df_mapa.dropna(subset=["lat", "lon"])

if not df_mapa.empty:
    # Atribuir cor RGB por categoria
    df_mapa["cor"] = df_mapa["categoria"].map(CORES_CATEGORIA).apply(lambda x: x if isinstance(x, list) else [149, 165, 166])

    # Tooltip
    df_mapa["tooltip_nome"] = df_mapa["nome"].fillna("")
    df_mapa["tooltip_cnpj"] = df_mapa["cnpj"].fillna("")
    df_mapa["tooltip_cat"] = df_mapa["categoria"].fillna("")
    df_mapa["tooltip_porte"] = df_mapa.get("porte_desc", pd.Series("", index=df_mapa.index)).fillna("")
    df_mapa["tooltip_mun"] = df_mapa["municipio"].fillna("")
    df_mapa["tooltip_tel"] = df_mapa.get("telefone", pd.Series("", index=df_mapa.index)).fillna("")
    df_mapa["tooltip_email"] = df_mapa.get("email", pd.Series("", index=df_mapa.index)).fillna("")

    # Centro e zoom
    centro = CENTROS_UF.get(uf_sel, DEFAULT_CENTER)

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_mapa,
        get_position=["lon", "lat"],
        get_color="cor",
        get_radius=600,
        radius_min_pixels=3,
        radius_max_pixels=15,
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 200, 0, 200],
    )

    view_state = pdk.ViewState(
        latitude=centro["lat"],
        longitude=centro["lon"],
        zoom=centro["zoom"],
        pitch=0,
    )

    tooltip = {
        "html": (
            "<b>{tooltip_nome}</b><br/>"
            "CNPJ: {tooltip_cnpj}<br/>"
            "Categoria: {tooltip_cat}<br/>"
            "Porte: {tooltip_porte}<br/>"
            "Municipio: {tooltip_mun}<br/>"
            "Tel: {tooltip_tel}<br/>"
            "Email: {tooltip_email}"
        ),
        "style": {
            "backgroundColor": "rgba(0,0,0,0.8)",
            "color": "white",
            "fontSize": "12px",
            "padding": "8px",
        },
    }

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
    )

    st.pydeck_chart(deck, use_container_width=True, height=650)

    if len(df_mapa) < total:
        st.caption(f"Exibindo {formatar_numero(len(df_mapa))} de {formatar_numero(total)} empresas (apenas com coordenadas).")

    # Legenda
    st.markdown("**Legenda:**  " + "  |  ".join(
        f'<span style="color:rgb({c[0]},{c[1]},{c[2]})">&#11044;</span> {cat}'
        for cat, c in CORES_CATEGORIA.items()
        if cat in df_mapa["categoria"].values
    ), unsafe_allow_html=True)

else:
    st.info(f"Nenhuma empresa com coordenadas em {uf_sel}.")

# === Distribuicoes ===
col_cat, col_porte = st.columns(2)

with col_cat:
    st.markdown("**Distribuicao por categoria**")
    if "categoria" in df_detail.columns and total > 0:
        cat_counts = df_detail["categoria"].value_counts().reset_index()
        cat_counts.columns = ["Categoria", "Total"]
        st.dataframe(cat_counts, use_container_width=True, hide_index=True, height=250)

with col_porte:
    st.markdown("**Distribuicao por porte**")
    if "porte_desc" in df_detail.columns and total > 0:
        porte_counts = df_detail["porte_desc"].value_counts().reset_index()
        porte_counts.columns = ["Porte", "Total"]
        st.dataframe(porte_counts, use_container_width=True, hide_index=True, height=250)

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
st.caption("Fontes: Receita Federal / CNPJ (Base dos Dados / BigQuery)")
