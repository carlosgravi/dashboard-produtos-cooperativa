"""API para carregar dados de empresas de transporte/logística/correios."""

import gzip
import json
import os

import numpy as np
import pandas as pd
import streamlit as st

from src.utils.constants import CATEGORIAS_EMPRESAS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "empresas")
UF_DIR = os.path.join(DATA_DIR, "uf")
CENTROIDES_PATH = os.path.join(DATA_DIR, "municipios_centroides.json")
CEP5_PATH = os.path.join(DATA_DIR, "cep5_coordenadas.json")
CEP_PATH = os.path.join(DATA_DIR, "cep_coordenadas.json")


def _carregar_json(arquivo):
    """Carrega arquivo JSON do diretório de dados."""
    caminho = os.path.join(DATA_DIR, arquivo)
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


@st.cache_data(ttl=86400)
def carregar_resumo_por_municipio():
    """Carrega resumo de empresas por município com coordenadas.

    Este é o arquivo principal para o mapa - dados agregados, leve.
    """
    dados = _carregar_json("resumo_por_municipio.json")
    if dados:
        return pd.DataFrame(dados)
    return pd.DataFrame()


@st.cache_data(ttl=86400)
def carregar_resumo_por_uf():
    """Carrega resumo de empresas por UF."""
    dados = _carregar_json("resumo_por_uf.json")
    if dados:
        return pd.DataFrame(dados)
    return pd.DataFrame()


@st.cache_data(ttl=86400)
def carregar_resumo_por_cnae():
    """Carrega resumo de empresas por CNAE."""
    dados = _carregar_json("resumo_por_cnae.json")
    if dados:
        return pd.DataFrame(dados)
    return pd.DataFrame()


@st.cache_data(ttl=86400)
def resumo_empresas_por_categoria():
    """Retorna contagem por categoria (transporte cargas, passageiros, etc.)."""
    df = carregar_resumo_por_cnae()
    if df.empty:
        return pd.DataFrame()
    if "categoria" in df.columns and "total" in df.columns:
        return df.groupby("categoria")["total"].sum().reset_index().sort_values(
            "total", ascending=False
        )
    return pd.DataFrame()


def filtrar_municipios(df, categoria=None, uf=None, fonte=None):
    """Filtra DataFrame de municípios por categoria, UF e fonte."""
    if df.empty:
        return df

    df_filtrado = df.copy()

    if uf and uf != "Todas":
        df_filtrado = df_filtrado[df_filtrado["uf"] == uf]

    # Se filtrar por categoria, usar a coluna específica como total
    if categoria and categoria != "Todas":
        col_cat = categoria.lower().replace(" ", "_").replace("ã", "a").replace("í", "i")
        if col_cat in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado[col_cat] > 0].copy()
            df_filtrado["total_filtrado"] = df_filtrado[col_cat]
        else:
            df_filtrado["total_filtrado"] = df_filtrado.get("total", 0)
    else:
        df_filtrado["total_filtrado"] = df_filtrado.get("total", 0)

    # Filtrar por fonte
    if fonte and fonte != "Todas":
        col_fonte = f"fonte_{fonte.lower()}"
        if col_fonte in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado[col_fonte] > 0].copy()

    return df_filtrado


# ============================================================
# Empresas individuais por UF
# ============================================================

@st.cache_data(ttl=86400)
def listar_ufs_com_dados_individuais():
    """Lista UFs que possuem data/empresas/uf/{UF}.json ou .json.gz."""
    if not os.path.isdir(UF_DIR):
        return []
    ufs = set()
    for f in os.listdir(UF_DIR):
        if f.endswith(".json.gz") and len(f) == 10:  # "SC.json.gz" = 10 chars
            ufs.add(f.replace(".json.gz", ""))
        elif f.endswith(".json") and len(f) == 7:  # "SC.json" = 7 chars
            ufs.add(f.replace(".json", ""))
    return sorted(ufs)


@st.cache_data(ttl=86400)
def _carregar_centroides():
    """Carrega mapeamento municipio|UF -> [lat, lon]."""
    if os.path.exists(CENTROIDES_PATH):
        with open(CENTROIDES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@st.cache_data(ttl=86400)
def _carregar_cep5():
    """Carrega mapeamento CEP-5 -> [lat, lon]."""
    if os.path.exists(CEP5_PATH):
        with open(CEP5_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@st.cache_data(ttl=86400)
def _carregar_cep_coords():
    """Carrega mapeamento CEP-8 -> [lat, lon] (logradouro)."""
    if os.path.exists(CEP_PATH):
        with open(CEP_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@st.cache_data(ttl=86400)
def carregar_empresas_uf(uf):
    """Carrega empresas individuais de uma UF (.json.gz ou .json).

    Preenche lat/lon: CEP-5 geocodificado > centroide municipio > vazio.
    Pequeno jitter para empresas no mesmo CEP-5.
    """
    df = pd.DataFrame()

    caminho_gz = os.path.join(UF_DIR, f"{uf}.json.gz")
    if os.path.exists(caminho_gz):
        with gzip.open(caminho_gz, "rt", encoding="utf-8") as f:
            dados = json.load(f)
        if dados:
            df = pd.DataFrame(dados)

    if df.empty:
        caminho = os.path.join(UF_DIR, f"{uf}.json")
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if dados:
                df = pd.DataFrame(dados)

    if df.empty:
        return df

    if "lat" not in df.columns or "lon" not in df.columns or "cep" not in df.columns:
        return df

    # 1) Coordenadas por CEP completo (logradouro - mais preciso)
    cep_coords = _carregar_cep_coords()
    sem_coord = df["lat"].isna() | df["lon"].isna()
    if sem_coord.any() and cep_coords:
        cep8 = df.loc[sem_coord, "cep"].astype(str).str[:8]
        df.loc[sem_coord, "lat"] = cep8.map(lambda k: (cep_coords.get(k) or [None, None])[0])
        df.loc[sem_coord, "lon"] = cep8.map(lambda k: (cep_coords.get(k) or [None, None])[1])

    # 2) Fallback: CEP-5 (bairro/distrito)
    sem_coord = df["lat"].isna() | df["lon"].isna()
    if sem_coord.any():
        cep5_coords = _carregar_cep5()
        if cep5_coords:
            cep5 = df.loc[sem_coord, "cep"].astype(str).str[:5]
            df.loc[sem_coord, "lat"] = cep5.map(lambda k: cep5_coords.get(k, [None, None])[0])
            df.loc[sem_coord, "lon"] = cep5.map(lambda k: cep5_coords.get(k, [None, None])[1])

    # 3) Fallback: centroide do municipio
    sem_coord = df["lat"].isna() | df["lon"].isna()
    if sem_coord.any() and "municipio" in df.columns:
        centroides = _carregar_centroides()
        if centroides:
            chaves = df.loc[sem_coord, "municipio"].astype(str) + "|" + df.loc[sem_coord, "uf"].astype(str)
            df.loc[sem_coord, "lat"] = chaves.map(lambda k: centroides.get(k, [None, None])[0])
            df.loc[sem_coord, "lon"] = chaves.map(lambda k: centroides.get(k, [None, None])[1])

    # 4) Pequeno jitter para nao empilhar empresas no mesmo ponto (~200m)
    tem_coord = df["lat"].notna() & df["lon"].notna()
    n = tem_coord.sum()
    if n > 0:
        rng = np.random.default_rng(42)
        df.loc[tem_coord, "lat"] = df.loc[tem_coord, "lat"].astype(float) + rng.uniform(-0.002, 0.002, size=n)
        df.loc[tem_coord, "lon"] = df.loc[tem_coord, "lon"].astype(float) + rng.uniform(-0.002, 0.002, size=n)

    return df


def filtrar_empresas_individuais(df, categoria=None, municipio=None, busca=None):
    """Filtra empresas individuais por categoria, município ou texto (nome/CNPJ/endereço)."""
    if df.empty:
        return df

    df_f = df.copy()

    if categoria and categoria != "Todas":
        df_f = df_f[df_f["categoria"] == categoria]

    if municipio and municipio != "Todos":
        df_f = df_f[df_f["municipio"] == municipio]

    if busca:
        busca = busca.strip()
        if busca:
            mask = (
                df_f["nome"].astype(str).str.contains(busca, case=False, na=False)
                | df_f["cnpj"].astype(str).str.contains(busca, case=False, na=False)
                | df_f["endereco"].astype(str).str.contains(busca, case=False, na=False)
            )
            df_f = df_f[mask]

    return df_f


def filtrar_empresas_avancado(df, categoria=None, municipio=None, porte=None,
                               capital_min=None, capital_max=None, busca=None):
    """Filtra empresas por categoria, município, porte, capital social e texto."""
    if df.empty:
        return df

    df_f = df.copy()

    if categoria and categoria != "Todas":
        df_f = df_f[df_f["categoria"] == categoria]

    if municipio and municipio != "Todos":
        df_f = df_f[df_f["municipio"] == municipio]

    if porte:
        df_f = df_f[df_f["porte_desc"].isin(porte)]

    if capital_min is not None and capital_min > 0:
        df_f = df_f[pd.to_numeric(df_f["capital_social"], errors="coerce").fillna(0) >= capital_min]

    if capital_max is not None and capital_max > 0:
        df_f = df_f[pd.to_numeric(df_f["capital_social"], errors="coerce").fillna(0) <= capital_max]

    if busca:
        busca = busca.strip()
        if busca:
            cols_busca = ["nome", "cnpj", "endereco"]
            if "nome_fantasia" in df_f.columns:
                cols_busca.append("nome_fantasia")
            if "email" in df_f.columns:
                cols_busca.append("email")
            mask = pd.Series(False, index=df_f.index)
            for col in cols_busca:
                mask = mask | df_f[col].astype(str).str.contains(busca, case=False, na=False)
            df_f = df_f[mask]

    return df_f
