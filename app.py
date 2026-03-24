"""Dashboard Transpocred - Entry Point."""

import streamlit as st

st.set_page_config(
    page_title="Dashboard Transpocred",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# === Navegacao ===
paginas = {
    "Transpocred": [
        st.Page("pages/1_visao_geral.py", title="Visao Geral", icon="🏠"),
        st.Page("pages/2_indicadores_financeiros.py", title="Indicadores Financeiros", icon="📊"),
    ],
    "Mercado": [
        st.Page("pages/3_panorama_cooperativismo.py", title="Panorama Cooperativismo", icon="🏦"),
        st.Page("pages/4_comparativo_mercado.py", title="Comparativo de Mercado", icon="🏆"),
        st.Page("pages/5_indicadores_economicos.py", title="Indicadores Economicos", icon="📉"),
    ],
    "Setor": [
        st.Page("pages/6_setor_transportes.py", title="Setor de Transportes", icon="🚛"),
        st.Page("pages/7_mapa_atuacao.py", title="Mapa de Atuacao", icon="🗺️"),
    ],
}

nav = st.navigation(paginas)

# === Sidebar ===
with st.sidebar:
    st.markdown("---")
    st.markdown(
        """
        **Transpocred**
        Cooperativa de Credito dos Trabalhadores
        em Transportes, Correios e Logistica

        *Sistema Ailos*
        """
    )
    st.markdown("---")
    st.caption("Dados publicos | BCB, ANTT, ANP")

nav.run()
