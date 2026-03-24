"""API da ANTT - RNTRC (Registro Nacional de Transportadores Rodoviarios de Cargas)."""

import json
import os

import pandas as pd
import requests
import streamlit as st

from src.utils.constants import ANTT_VEICULOS_CSV, ANTT_TRANSPORTADORES_CKAN

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _carregar_cache(subdir, arquivo):
    """Tenta carregar dados do cache local JSON."""
    caminho = os.path.join(DATA_DIR, subdir, arquivo)
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _obter_url_transportadores():
    """Obtem URL mais recente do CSV de transportadores via API CKAN."""
    try:
        resp = requests.get(ANTT_TRANSPORTADORES_CKAN, timeout=30)
        resp.raise_for_status()
        dados = resp.json()
        resources = dados.get("result", {}).get("resources", [])
        # Pegar o recurso mais recente (ultimo da lista)
        for r in reversed(resources):
            url = r.get("url", "")
            if "transportadores" in url.lower() and url.endswith(".csv"):
                return url
    except Exception:
        pass
    return None


@st.cache_data(ttl=86400)
def buscar_rntrc_veiculos():
    """Busca dados de veiculos RNTRC da ANTT."""
    # Tentar cache local
    cache = _carregar_cache("antt", "rntrc_veiculos_resumo.json")
    if cache is not None and isinstance(cache, dict) and "por_uf" in cache:
        return cache

    try:
        df = pd.read_csv(
            ANTT_VEICULOS_CSV,
            sep=";",
            encoding="latin-1",
            dtype=str,
            on_bad_lines="skip",
        )
        df.columns = [c.strip().lower() for c in df.columns]
        # Normalizar nomes de colunas para o formato esperado
        renames = {}
        for c in df.columns:
            if "uf" in c and "veic" in c:
                renames[c] = "UF_Veiculo"
            elif c == "uf":
                renames[c] = "UF_Veiculo"
            elif "tipo" in c and "veic" in c:
                renames[c] = "Tipo_Veiculo"
            elif c == "situacao" or "situacao" in c:
                renames[c] = "Situacao"
            elif "ano" in c and "fabric" in c:
                renames[c] = "Ano_Fabricacao"
            elif c == "marca":
                renames[c] = "Marca"
        df = df.rename(columns=renames)
        return df
    except Exception as e:
        st.error(f"Erro ao buscar dados RNTRC de veiculos: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=86400)
def buscar_rntrc_transportadores_resumo():
    """Busca resumo de transportadores RNTRC."""
    # Tentar cache local
    cache = _carregar_cache("antt", "rntrc_transportadores_resumo.json")
    if cache is not None and isinstance(cache, list):
        return pd.DataFrame(cache)

    # Obter URL dinamicamente via CKAN
    url_csv = _obter_url_transportadores()
    if not url_csv:
        st.error("Nao foi possivel obter a URL do CSV de transportadores da ANTT.")
        return pd.DataFrame()

    try:
        chunks = pd.read_csv(
            url_csv,
            sep=";",
            encoding="latin-1",
            dtype=str,
            chunksize=50000,
            on_bad_lines="skip",
        )
        frames = []
        for chunk in chunks:
            chunk.columns = [c.strip().lower() for c in chunk.columns]
            # Identificar colunas de UF, categoria e situacao
            col_uf = next((c for c in chunk.columns if c == "uf"), None)
            col_cat = next((c for c in chunk.columns if "categoria" in c), None)
            col_sit = next((c for c in chunk.columns if "situacao" in c), None)
            if col_uf and col_cat and col_sit:
                chunk = chunk.rename(columns={col_uf: "UF", col_cat: "Categoria", col_sit: "Situacao"})
                resumo = chunk.groupby(["UF", "Categoria", "Situacao"]).size().reset_index(name="Quantidade")
                frames.append(resumo)
        if frames:
            df = pd.concat(frames, ignore_index=True)
            return df.groupby(["UF", "Categoria", "Situacao"])["Quantidade"].sum().reset_index()
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao buscar dados RNTRC de transportadores: {e}")
        return pd.DataFrame()


def resumo_veiculos_por_uf(df_veiculos):
    """Agrega veiculos por UF."""
    if isinstance(df_veiculos, dict) and "por_uf" in df_veiculos:
        df = pd.DataFrame(df_veiculos["por_uf"])
        if "Total" in df.columns and "Total_Veiculos" not in df.columns:
            df = df.rename(columns={"Total": "Total_Veiculos"})
        if "UF_Veiculo" not in df.columns:
            for c in df.columns:
                if c != "Total_Veiculos":
                    df = df.rename(columns={c: "UF_Veiculo"})
                    break
        return df.sort_values("Total_Veiculos", ascending=False)
    if not isinstance(df_veiculos, pd.DataFrame) or df_veiculos.empty:
        return pd.DataFrame()
    col_uf = "UF_Veiculo" if "UF_Veiculo" in df_veiculos.columns else "UF"
    return df_veiculos.groupby(col_uf).size().reset_index(name="Total_Veiculos").sort_values(
        "Total_Veiculos", ascending=False
    )


def resumo_veiculos_por_tipo(df_veiculos):
    """Agrega veiculos por tipo."""
    if isinstance(df_veiculos, dict) and "por_tipo" in df_veiculos:
        return pd.DataFrame(df_veiculos["por_tipo"]).sort_values("Total", ascending=False)
    if not isinstance(df_veiculos, pd.DataFrame) or df_veiculos.empty:
        return pd.DataFrame()
    if "Tipo_Veiculo" not in df_veiculos.columns:
        return pd.DataFrame()
    return df_veiculos.groupby("Tipo_Veiculo").size().reset_index(name="Total").sort_values(
        "Total", ascending=False
    )


def resumo_idade_frota(df_veiculos):
    """Calcula distribuicao de idade da frota."""
    if isinstance(df_veiculos, dict) and "por_idade" in df_veiculos:
        return pd.DataFrame(df_veiculos["por_idade"])
    if not isinstance(df_veiculos, pd.DataFrame) or df_veiculos.empty:
        return pd.DataFrame()
    if "Ano_Fabricacao" not in df_veiculos.columns:
        return pd.DataFrame()
    from datetime import datetime
    df = df_veiculos.copy()
    df["Ano_Fabricacao"] = pd.to_numeric(df["Ano_Fabricacao"], errors="coerce")
    df = df.dropna(subset=["Ano_Fabricacao"])
    df["Idade"] = datetime.now().year - df["Ano_Fabricacao"]
    bins = [0, 5, 10, 15, 20, 100]
    labels = ["0-5 anos", "6-10 anos", "11-15 anos", "16-20 anos", "20+ anos"]
    df["Faixa_Idade"] = pd.cut(df["Idade"], bins=bins, labels=labels, right=True)
    return df.groupby("Faixa_Idade", observed=True).size().reset_index(name="Quantidade")


def resumo_transportadores_por_categoria(df_transportadores):
    """Agrega transportadores por categoria (TAC, ETC, CTC)."""
    if df_transportadores.empty or "Categoria" not in df_transportadores.columns:
        return pd.DataFrame()
    return df_transportadores.groupby("Categoria")["Quantidade"].sum().reset_index().sort_values(
        "Quantidade", ascending=False
    )
