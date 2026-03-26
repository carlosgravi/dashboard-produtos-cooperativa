"""Dashboard Transpocred - Entry Point."""

import streamlit as st

st.set_page_config(
    page_title="Dashboard Transpocred",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    st.markdown("---")
    st.markdown(
        """
        **Transpocred**
        Cooperativa de Crédito dos Trabalhadores
        em Transportes, Correios e Logística

        *Sistema Ailos*
        """
    )
    st.markdown("---")
    st.caption("Dados públicos | BCB, ANTT, ANP, RFB, CGU, PNCP")

nav.run()
