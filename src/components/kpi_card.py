"""Componentes de KPI cards para o dashboard."""

import streamlit as st


def kpi_card(label, valor, delta=None, delta_color="normal", help_text=None):
    """Renderiza um KPI card usando st.metric.

    Args:
        label: Titulo do KPI
        valor: Valor formatado (string)
        delta: Variacao (string ou numero, opcional)
        delta_color: 'normal', 'inverse', ou 'off'
        help_text: Texto de ajuda (tooltip)
    """
    st.metric(
        label=label,
        value=valor,
        delta=delta,
        delta_color=delta_color,
        help=help_text,
    )


def kpi_row(kpis, colunas=None):
    """Renderiza uma linha de KPI cards.

    Args:
        kpis: Lista de dicts com keys: label, valor, delta (opcional), delta_color (opcional), help (opcional)
        colunas: Numero de colunas (padrao: len(kpis))
    """
    n = colunas or len(kpis)
    cols = st.columns(n)
    for i, kpi in enumerate(kpis):
        if i >= n:
            break
        with cols[i]:
            kpi_card(
                label=kpi.get("label", ""),
                valor=kpi.get("valor", "—"),
                delta=kpi.get("delta"),
                delta_color=kpi.get("delta_color", "normal"),
                help_text=kpi.get("help"),
            )
