"""APIs do Banco Central do Brasil: SGS, IF.data, BcBase, Sedes."""

import json
import os

import pandas as pd
import requests
import streamlit as st
import urllib.parse
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _carregar_cache(subdir, arquivo):
    """Tenta carregar dados do cache local JSON."""
    caminho = os.path.join(DATA_DIR, subdir, arquivo)
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
        if isinstance(dados, list):
            return pd.DataFrame(dados)
        if isinstance(dados, dict):
            return dados
    return None


# ============================================================
# SGS - Sistema Gerenciador de Séries Temporais
# ============================================================

@st.cache_data(ttl=3600)
def buscar_serie_sgs(codigo, data_inicio=None, data_fim=None):
    """Busca série temporal do SGS/BCB.

    Args:
        codigo: Código da série SGS (ex: 4189 para Selic)
        data_inicio: Data inicial no formato 'dd/mm/yyyy' (opcional)
        data_fim: Data final no formato 'dd/mm/yyyy' (opcional)

    Returns:
        DataFrame com colunas ['data', 'valor']
    """
    # Tentar cache local
    from src.utils.constants import SGS
    nome_serie = None
    for nome, cod in SGS.items():
        if cod == codigo:
            nome_serie = nome.lower()
            break
    if nome_serie:
        cache = _carregar_cache("bcb", f"sgs_{nome_serie}.json")
        if cache is not None and isinstance(cache, pd.DataFrame) and not cache.empty:
            df = cache.copy()
            df["data"] = pd.to_datetime(df["data"])
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
            # Aplicar filtros de data se fornecidos
            if data_inicio:
                dt_ini = pd.to_datetime(data_inicio, format="%d/%m/%Y")
                df = df[df["data"] >= dt_ini]
            if data_fim:
                dt_fim = pd.to_datetime(data_fim, format="%d/%m/%Y")
                df = df[df["data"] <= dt_fim]
            return df.dropna(subset=["valor"]).reset_index(drop=True)

    # Fallback: buscar da API
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
    params = {"formato": "json"}
    if data_inicio:
        params["dataInicial"] = data_inicio
    if data_fim:
        params["dataFinal"] = data_fim

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        dados = resp.json()
        if not dados:
            return pd.DataFrame(columns=["data", "valor"])
        df = pd.DataFrame(dados)
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        return df.dropna(subset=["valor"]).reset_index(drop=True)
    except Exception as e:
        st.error(f"Erro ao buscar série SGS {codigo}: {e}")
        return pd.DataFrame(columns=["data", "valor"])


@st.cache_data(ttl=3600)
def buscar_multiplas_series_sgs(codigos_dict, data_inicio=None, data_fim=None):
    """Busca múltiplas séries SGS e retorna DataFrame unificado.

    Args:
        codigos_dict: Dict {nome: codigo_sgs}
        data_inicio: Data inicial 'dd/mm/yyyy'
        data_fim: Data final 'dd/mm/yyyy'

    Returns:
        DataFrame com coluna 'data' e uma coluna por série
    """
    resultado = None
    for nome, codigo in codigos_dict.items():
        df = buscar_serie_sgs(codigo, data_inicio, data_fim)
        if df.empty:
            continue
        df = df.rename(columns={"valor": nome})
        if resultado is None:
            resultado = df
        else:
            resultado = pd.merge(resultado, df, on="data", how="outer")
    if resultado is not None:
        resultado = resultado.sort_values("data").reset_index(drop=True)
    else:
        resultado = pd.DataFrame()
    return resultado


# ============================================================
# IF.data - Informações Financeiras de Instituições
# ============================================================

IFDATA_BASE = "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata"


def _get_ifdata_datas_base():
    """Retorna lista das datas-base disponíveis no IF.data (trimestres passados)."""
    hoje = datetime.now()
    datas = []
    for ano in range(hoje.year, hoje.year - 4, -1):
        for mes in [12, 9, 6, 3]:
            # Dados trimestrais só ficam disponíveis ~2 meses após o fechamento
            # Então só incluímos trimestres com pelo menos 2 meses de defasagem
            dt_trimestre = datetime(ano, mes, 1)
            if dt_trimestre < hoje - timedelta(days=60):
                datas.append(f"{ano}{mes:02d}")
    return datas


@st.cache_data(ttl=86400)
def buscar_ifdata_valores(relatorio, data_base=None, cnpj_8=None, tipo_instituicao=1, timeout=120):
    """Busca dados do IF.data (BCB OLINDA).

    Args:
        relatorio: Número do relatório (1=Resumo, 3=Passivo, 4=DRE, etc.)
        data_base: Data-base no formato 'YYYYMM' (ex: '202312'). Se None, usa mais recente.
        cnpj_8: CNPJ 8 dígitos para filtrar (ex: '08075352'). Se None, retorna todos.
        tipo_instituicao: Tipo (1=Congl.Prudenciais, 2=Congl.Financeiros, 3=Individuais, 4=Câmbio)
        timeout: Timeout em segundos (padrão 60, usar 300 para queries completas)

    Returns:
        DataFrame com os dados do relatório (coluna Valor normalizada de Saldo)
    """
    # Tentar cache local para ranking (todas cooperativas, sem filtro CNPJ)
    if cnpj_8 is None and relatorio == 1:
        cache = _carregar_cache("bcb", "ifdata_todas_cooperativas.json")
        if cache is not None and isinstance(cache, pd.DataFrame) and not cache.empty:
            if "Valor" not in cache.columns and "Saldo" in cache.columns:
                cache["Valor"] = pd.to_numeric(cache["Saldo"], errors="coerce")
            return cache

    if data_base is None:
        datas = _get_ifdata_datas_base()
        data_base = datas[0] if datas else "202312"

    # Montar URL manualmente para evitar double-encoding do @
    url = (
        f"{IFDATA_BASE}/IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,Relatorio=@Relatorio)"
        f"?@AnoMes={data_base}&@TipoInstituicao={tipo_instituicao}&@Relatorio=%27{relatorio}%27"
        f"&$format=json&$top=10000"
    )
    if cnpj_8:
        url += "&$filter=" + urllib.parse.quote(f"CodInst eq '{cnpj_8}'")

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        dados = resp.json()
        registros = dados.get("value", [])
        if not registros:
            return pd.DataFrame()
        df = pd.DataFrame(registros)
        # Normalizar: a API retorna "Saldo", renomear para "Valor" para uso interno
        if "Saldo" in df.columns:
            df["Valor"] = pd.to_numeric(df["Saldo"], errors="coerce")
        # Normalizar nome da conta: "NomeColuna" tem nomes legíveis (ex: "Ativo Total")
        if "NomeConta" not in df.columns:
            if "NomeColuna" in df.columns:
                df["NomeConta"] = df["NomeColuna"]
            elif "DescricaoColuna" in df.columns:
                df["NomeConta"] = df["DescricaoColuna"]
            elif "Conta" in df.columns:
                df["NomeConta"] = df["Conta"]
        return df
    except requests.exceptions.Timeout:
        st.error(
            f"Timeout ao buscar dados do IF.data (relatório {relatorio}). "
            "Os dados completos podem levar até 5 minutos para carregar. Tente novamente."
        )
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao buscar IF.data (relatório {relatorio}): {e}")
        return pd.DataFrame()


_IFDATA_CACHE_NOMES = {
    1: "resumo",
    3: "passivo",
    4: "dre",
    5: "capital",
    11: "credito_pf",
    13: "credito_pj",
}


@st.cache_data(ttl=86400)
def buscar_ifdata_transpocred(relatorio, data_base=None):
    """Busca dados IF.data filtrados para a Transpocred."""
    # Tentar cache local
    nome = _IFDATA_CACHE_NOMES.get(relatorio)
    if nome:
        cache = _carregar_cache("bcb", f"ifdata_transpocred_{nome}.json")
        if cache is not None and isinstance(cache, pd.DataFrame) and not cache.empty:
            if "Valor" not in cache.columns and "Saldo" in cache.columns:
                cache["Valor"] = pd.to_numeric(cache["Saldo"], errors="coerce")
            return cache

    # Fallback: buscar da API
    from src.utils.constants import TRANSPOCRED_CNPJ_8
    return buscar_ifdata_valores(relatorio, data_base, cnpj_8=TRANSPOCRED_CNPJ_8)


@st.cache_data(ttl=86400)
def buscar_ifdata_evolucao(relatorio, cnpj_8=None, n_trimestres=6):
    """Busca dados IF.data para múltiplas datas-base (evolução trimestral).

    Usa chamadas paralelas para reduzir tempo de espera.

    Returns:
        DataFrame com todos os trimestres concatenados
    """
    # Tentar cache local (evolução pré-carregada com 12 trimestres)
    if relatorio == 1 and cnpj_8:
        from src.utils.constants import TRANSPOCRED_CNPJ_8
        if cnpj_8 == TRANSPOCRED_CNPJ_8:
            cache = _carregar_cache("bcb", "ifdata_transpocred_evolucao.json")
            if cache is not None and isinstance(cache, pd.DataFrame) and not cache.empty:
                if "Valor" not in cache.columns and "Saldo" in cache.columns:
                    cache["Valor"] = pd.to_numeric(cache["Saldo"], errors="coerce")
                return cache

    # Fallback: buscar da API
    from concurrent.futures import ThreadPoolExecutor, as_completed

    datas = _get_ifdata_datas_base()[:n_trimestres]

    def _buscar(dt):
        df = buscar_ifdata_valores(relatorio, dt, cnpj_8)
        if not df.empty:
            df["DataBase"] = dt
        return df

    frames = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futuros = {executor.submit(_buscar, dt): dt for dt in datas}
        for futuro in as_completed(futuros):
            try:
                df = futuro.result()
                if not df.empty:
                    frames.append(df)
            except Exception:
                pass

    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()


# ============================================================
# BcBase - Cadastro de Cooperativas
# ============================================================

@st.cache_data(ttl=86400)
def buscar_cooperativas_bcbase():
    """Busca lista de cooperativas de crédito do cadastro BCB."""
    url = (
        "https://olinda.bcb.gov.br/olinda/servico/BcBase/versao/v2/odata/"
        "CooperativasDeCredito"
    )
    params = {
        "$format": "json",
        "$top": 5000,
    }
    try:
        resp = requests.get(url, params=params, timeout=120)
        resp.raise_for_status()
        dados = resp.json()
        registros = dados.get("value", [])
        return pd.DataFrame(registros) if registros else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao buscar cadastro de cooperativas (BcBase): {e}")
        return pd.DataFrame()


# ============================================================
# Sedes de Cooperativas (para mapa)
# ============================================================

@st.cache_data(ttl=86400)
def buscar_sedes_cooperativas():
    """Busca cooperativas de crédito ativas via BcBase v2."""
    from src.utils.constants import BCBASE_URL, UF_NOME_PARA_SIGLA

    # Tentar cache local
    cache = _carregar_cache("bcb", "sedes_cooperativas.json")
    if cache is not None and isinstance(cache, pd.DataFrame) and not cache.empty:
        return cache

    # Fallback: buscar via BcBase v2 Cooperativas
    from datetime import datetime as _dt
    data_ref = _dt.now().strftime("01/%m/%Y")
    # Montar URL manualmente para evitar double-encoding
    url = (
        f"{BCBASE_URL}/Cooperativas(dataBase=@dataBase)"
        f"?@dataBase='{data_ref}'"
        f"&$format=json"
        f"&$filter=codigoTipoSituacaoPessoaJuridica eq 3"
    )
    try:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        dados = resp.json()
        registros = dados.get("value", [])
        if not registros:
            return pd.DataFrame()
        df = pd.DataFrame(registros)
        # Criar coluna UF (sigla) a partir do nome do estado
        if "nomeDaUnidadeFederativa" in df.columns:
            df["UF"] = df["nomeDaUnidadeFederativa"].map(UF_NOME_PARA_SIGLA)
        return df
    except Exception as e:
        st.error(f"Erro ao buscar cooperativas (BcBase): {e}")
        return pd.DataFrame()


@st.cache_data(ttl=86400)
def carregar_ranking_historico():
    """Carrega ranking histórico de todas as cooperativas (múltiplos trimestres).

    Dados pré-coletados em data/bcb/ifdata_ranking_historico.json via:
        python scripts/atualizar_dados.py --ranking-historico

    Returns:
        DataFrame com dados de todas as cooperativas em múltiplos trimestres, ou None se cache não existe.
    """
    cache = _carregar_cache("bcb", "ifdata_ranking_historico.json")
    if cache is not None and isinstance(cache, pd.DataFrame) and not cache.empty:
        if "Valor" not in cache.columns and "Saldo" in cache.columns:
            cache["Valor"] = pd.to_numeric(cache["Saldo"], errors="coerce")
        return cache
    return None


@st.cache_data(ttl=86400)
def buscar_instituicoes_funcionamento(tipo_instituicao=None):
    """Busca instituições em funcionamento no BCB."""
    url = (
        "https://olinda.bcb.gov.br/olinda/servico/"
        "Instituicoes_em_funcionamento/versao/v2/odata/"
        "IfsFuncionamento"
    )
    params = {
        "$format": "json",
        "$top": 10000,
    }
    if tipo_instituicao:
        params["$filter"] = f"TipoInstituicao eq '{tipo_instituicao}'"

    try:
        resp = requests.get(url, params=params, timeout=120)
        resp.raise_for_status()
        dados = resp.json()
        registros = dados.get("value", [])
        return pd.DataFrame(registros) if registros else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao buscar instituições em funcionamento: {e}")
        return pd.DataFrame()
