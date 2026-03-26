"""Dashboard Transpocred - Entry Point."""

import streamlit as st

st.set_page_config(
    page_title="Dashboard Transpocred",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# === Sidebar escuro com identidade Transpocred ===
st.markdown("""
<style>
/* Fundo escuro no sidebar */
[data-testid="stSidebar"] {
    background-color: #165C7D;
}

/* Texto geral do sidebar em branco */
[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}

/* Títulos de grupo do menu (Transpocred, Mercado, Setor, Sobre) */
[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] span,
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4 {
    color: #FFA300 !important;
    font-weight: 700;
}

/* Links do menu */
[data-testid="stSidebar"] a {
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] a:hover {
    color: #FFA300 !important;
}

/* Item de menu ativo: fundo teal com texto branco */
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"],
[data-testid="stSidebar"] .stNavLink[aria-selected="true"] {
    background-color: #007D89 !important;
}

/* Linha divisória no sidebar */
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.2) !important;
}

/* Caption no sidebar */
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {
    color: rgba(255,255,255,0.7) !important;
}
</style>
""", unsafe_allow_html=True)

# === Navegação ===
paginas = {
    "Transpocred": [
        st.Page("pages/1_visao_geral.py", title="Visão Geral", icon="🏠"),
        st.Page("pages/2_indicadores_financeiros.py", title="Indicadores Financeiros", icon="📊"),
    ],
    "Mercado": [
        st.Page("pages/3_panorama_cooperativismo.py", title="Panorama Cooperativismo", icon="🏦"),
        st.Page("pages/4_comparativo_mercado.py", title="Comparativo de Mercado", icon="🏆"),
        st.Page("pages/5_indicadores_economicos.py", title="Indicadores Econômicos", icon="📉"),
        st.Page("pages/12_market_share.py", title="Market Share", icon="📈"),
    ],
    "Setor": [
        st.Page("pages/6_setor_transportes.py", title="Setor de Transportes", icon="🚛"),
        st.Page("pages/7_mapa_atuacao.py", title="Mapa de Atuação", icon="🗺️"),
        st.Page("pages/8_mapa_empresas.py", title="Mapa de Empresas", icon="📍"),
        st.Page("pages/9_compliance.py", title="Compliance", icon="🔍"),
        st.Page("pages/10_diretorio_empresas.py", title="Diretório de Empresas", icon="📋"),
    ],
    "Sobre": [
        st.Page("pages/11_documentacao.py", title="Documentação Técnica", icon="📄"),
    ],
}

nav = st.navigation(paginas)

# === Sidebar ===
with st.sidebar:
    st.image("assets/logo_transpocred.svg")
    st.markdown("---")
    st.caption("Dados públicos | BCB, ANTT, ANP, RFB, CGU, PNCP")

nav.run()
