"""API da ANP - Preços de combustíveis (Diesel)."""

import json
import os

import pandas as pd
import requests
import streamlit as st
from datetime import datetime

from src.utils.constants import ANP_DIESEL_RECENTE_URL, ANP_DIESEL_MENSAL_URL

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _carregar_cache(subdir, arquivo):
    """Tenta carregar dados do cache local JSON."""
    caminho = os.path.join(DATA_DIR, subdir, arquivo)
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
        if isinstance(dados, list):
            return pd.DataFrame(dados)
    return None


def _url_diesel_mensal(ano, mes):
    """Monta URL do CSV mensal de diesel conforme padrão do ano."""
    if ano >= 2026:
        return f"{ANP_DIESEL_MENSAL_URL}/{ano}/{mes:02d}-dados-abertos-precos-diesel-gnv.csv"
    else:
        return f"{ANP_DIESEL_MENSAL_URL}/{ano}/precos-diesel-gnv-{mes:02d}.csv"


def _ler_csv_anp(url):
    """Lê CSV de diesel da ANP e retorna DataFrame normalizado."""
    df = pd.read_csv(
        url,
        sep=";",
        encoding="latin-1",
        dtype=str,
        on_bad_lines="skip",
    )
    df.columns = [c.strip() for c in df.columns]

    # Identificar colunas por conteúdo (nomes podem variar entre versões)
    col_uf = next((c for c in df.columns if "Estado" in c and "Sigla" in c), None)
    col_produto = next((c for c in df.columns if "Produto" in c), None)
    col_valor = next((c for c in df.columns if "Valor de Venda" in c), None)
    col_data = next((c for c in df.columns if "Data da Coleta" in c), None)

    if not all([col_uf, col_produto, col_valor, col_data]):
        return pd.DataFrame()

    df = df[[col_uf, col_produto, col_valor, col_data]]
    df.columns = ["UF", "Produto", "Valor_Venda", "Data_Coleta"]
    df = df[df["Produto"].str.contains("DIESEL", case=False, na=False)]
    df["Valor_Venda"] = df["Valor_Venda"].str.replace(",", ".").astype(float, errors="ignore")
    df["Valor_Venda"] = pd.to_numeric(df["Valor_Venda"], errors="coerce")
    df["Data_Coleta"] = pd.to_datetime(df["Data_Coleta"], format="%d/%m/%Y", errors="coerce")
    return df.dropna(subset=["Valor_Venda"])


@st.cache_data(ttl=86400)
def buscar_precos_diesel_recentes(n_semanas=4):
    """Busca preços recentes de diesel da ANP."""
    # Tentar cache local
    cache = _carregar_cache("anp", "diesel_recente.json")
    if cache is not None and not cache.empty:
        cache["Valor_Venda"] = pd.to_numeric(cache["Valor_Venda"], errors="coerce")
        cache["Data_Coleta"] = pd.to_datetime(cache["Data_Coleta"], errors="coerce")
        return cache.dropna(subset=["Valor_Venda"])

    # Tentar URL de últimas 4 semanas (sempre atualizada)
    try:
        df = _ler_csv_anp(ANP_DIESEL_RECENTE_URL)
        if not df.empty:
            return df
    except Exception:
        pass

    # Fallback: CSVs mensais
    hoje = datetime.now()
    frames = []
    for i in range(3):
        ano = hoje.year
        mes = hoje.month - i
        if mes <= 0:
            mes += 12
            ano -= 1
        try:
            url = _url_diesel_mensal(ano, mes)
            df = _ler_csv_anp(url)
            if not df.empty:
                frames.append(df)
        except Exception:
            continue

    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()


@st.cache_data(ttl=86400)
def buscar_historico_diesel(ano_inicio=None):
    """Busca histórico de preços de diesel (semestral)."""
    # Tentar cache local
    cache = _carregar_cache("anp", "diesel_historico.json")
    if cache is not None and not cache.empty:
        cache["Preco_Medio"] = pd.to_numeric(cache["Preco_Medio"], errors="coerce")
        if "Data" in cache.columns:
            cache["Data"] = pd.to_datetime(cache["Data"], errors="coerce")
        return cache

    # Fallback: buscar CSVs mensais
    if ano_inicio is None:
        ano_inicio = datetime.now().year - 2
    hoje = datetime.now()
    frames = []

    for ano in range(ano_inicio, hoje.year + 1):
        for mes in [1, 6]:
            if ano == hoje.year and mes > hoje.month:
                continue
            try:
                url = _url_diesel_mensal(ano, mes)
                df = _ler_csv_anp(url)
                if not df.empty:
                    resumo = df.groupby("UF").agg(
                        Preco_Medio=("Valor_Venda", "mean"),
                        Data=("Data_Coleta", "max"),
                    ).reset_index()
                    resumo["Ano"] = ano
                    resumo["Mes"] = mes
                    frames.append(resumo)
            except Exception:
                continue

    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()


def calcular_preco_medio_diesel_por_uf(df_diesel):
    """Calcula preço médio do diesel por UF a partir dos dados brutos."""
    if df_diesel.empty or "Valor_Venda" not in df_diesel.columns:
        return pd.DataFrame()
    return (
        df_diesel.groupby("UF")["Valor_Venda"]
        .mean()
        .reset_index()
        .rename(columns={"Valor_Venda": "Preco_Medio"})
        .sort_values("Preco_Medio", ascending=False)
    )


def calcular_preco_medio_nacional(df_diesel):
    """Calcula preço médio nacional do diesel."""
    if df_diesel.empty or "Valor_Venda" not in df_diesel.columns:
        return None
    return df_diesel["Valor_Venda"].mean()
