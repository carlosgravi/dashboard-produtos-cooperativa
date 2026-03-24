"""Componentes de graficos Plotly para o dashboard."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import requests

from src.utils.constants import CORES, PALETA_SEQUENCIAL, LAYOUT_PADRAO, GEOJSON_BRASIL_URL


def _aplicar_layout(fig, titulo=None, altura=400):
    """Aplica layout padrao ao grafico Plotly."""
    layout = dict(LAYOUT_PADRAO)
    if titulo:
        layout["title"] = dict(text=titulo, x=0.5, xanchor="center")
    layout["height"] = altura
    fig.update_layout(**layout)
    return fig


def grafico_linha(df, x, y, titulo=None, cor=None, altura=400, formato_y=None):
    """Grafico de linha simples."""
    fig = px.line(
        df, x=x, y=y,
        color_discrete_sequence=[cor or CORES["verde_ailos"]],
    )
    fig.update_traces(line=dict(width=2.5))
    if formato_y:
        fig.update_yaxes(tickformat=formato_y)
    return _aplicar_layout(fig, titulo, altura)


def grafico_linhas_multiplas(df, x, y_cols, nomes=None, titulo=None, altura=400, formato_y=None):
    """Grafico com multiplas linhas."""
    fig = go.Figure()
    cores = PALETA_SEQUENCIAL
    nomes = nomes or y_cols
    for i, col in enumerate(y_cols):
        if col not in df.columns:
            continue
        fig.add_trace(go.Scatter(
            x=df[x],
            y=df[col],
            mode="lines+markers",
            name=nomes[i] if i < len(nomes) else col,
            line=dict(color=cores[i % len(cores)], width=2),
            marker=dict(size=4),
        ))
    if formato_y:
        fig.update_yaxes(tickformat=formato_y)
    return _aplicar_layout(fig, titulo, altura)


def grafico_barras(df, x, y, titulo=None, cor=None, horizontal=False, altura=400, formato_valores=None, texto=None):
    """Grafico de barras."""
    if horizontal:
        fig = px.bar(
            df, x=y, y=x, orientation="h",
            color_discrete_sequence=[cor or CORES["verde_ailos"]],
            text=texto,
        )
    else:
        fig = px.bar(
            df, x=x, y=y,
            color_discrete_sequence=[cor or CORES["verde_ailos"]],
            text=texto,
        )
    if texto:
        fig.update_traces(textposition="outside")
    return _aplicar_layout(fig, titulo, altura)


def grafico_barras_agrupadas(df, x, y, cor, titulo=None, altura=400):
    """Grafico de barras agrupadas por categoria."""
    fig = px.bar(
        df, x=x, y=y, color=cor, barmode="group",
        color_discrete_sequence=PALETA_SEQUENCIAL,
    )
    return _aplicar_layout(fig, titulo, altura)


def grafico_pizza(df, valores, nomes, titulo=None, altura=400):
    """Grafico de pizza/donut."""
    fig = px.pie(
        df, values=valores, names=nomes,
        color_discrete_sequence=PALETA_SEQUENCIAL,
        hole=0.4,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return _aplicar_layout(fig, titulo, altura)


@st.cache_data(ttl=86400)
def _carregar_geojson_brasil():
    """Carrega GeoJSON dos estados brasileiros."""
    try:
        resp = requests.get(GEOJSON_BRASIL_URL, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Erro ao carregar mapa do Brasil: {e}")
        return None


def grafico_mapa_brasil(df, coluna_uf, coluna_valor, titulo=None, altura=500, color_scale=None):
    """Mapa coropletico do Brasil por UF.

    Args:
        df: DataFrame com dados por UF
        coluna_uf: Nome da coluna com siglas UF
        coluna_valor: Nome da coluna com valores
        titulo: Titulo do grafico
        altura: Altura em pixels
        color_scale: Escala de cores (padrao: Greens)
    """
    geojson = _carregar_geojson_brasil()
    if geojson is None:
        st.warning("Nao foi possivel carregar o mapa.")
        return None

    fig = px.choropleth(
        df,
        geojson=geojson,
        locations=coluna_uf,
        featureidkey="properties.sigla",
        color=coluna_valor,
        color_continuous_scale=color_scale or "Greens",
        scope="south america",
        hover_name=coluna_uf,
        hover_data={coluna_valor: ":,.0f"},
    )
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor="white",
    )
    layout = dict(LAYOUT_PADRAO)
    if titulo:
        layout["title"] = dict(text=titulo, x=0.5, xanchor="center")
    layout["height"] = altura
    layout["margin"] = dict(l=0, r=0, t=50, b=0)
    fig.update_layout(**layout)
    return fig
