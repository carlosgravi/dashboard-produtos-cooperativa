"""API para carregar dados de compliance empresarial."""

import json
import os

import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "empresas")
COMPLIANCE_DIR = os.path.join(DATA_DIR, "compliance")


def _carregar_json(caminho):
    """Carrega arquivo JSON."""
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


@st.cache_data(ttl=86400)
def carregar_compliance_uf(uf):
    """Carrega dados de compliance de uma UF.

    Returns:
        DataFrame com colunas: cnpj, nome, ceis, cnep, pncp_contratos, consultado_em
    """
    caminho = os.path.join(COMPLIANCE_DIR, f"{uf}_compliance.json")
    dados = _carregar_json(caminho)
    if dados:
        return pd.DataFrame(dados)
    return pd.DataFrame()


@st.cache_data(ttl=86400)
def carregar_resumo_compliance():
    """Carrega resumo de compliance de todas as UFs.

    Returns:
        Dict com chaves por UF, cada uma com totais de sancoes/contratos.
    """
    caminho = os.path.join(COMPLIANCE_DIR, "resumo_geral.json")
    dados = _carregar_json(caminho)
    if dados:
        return dados
    return {}


@st.cache_data(ttl=86400)
def listar_ufs_com_compliance():
    """Lista UFs que possuem dados de compliance."""
    if not os.path.isdir(COMPLIANCE_DIR):
        return []
    ufs = []
    for f in os.listdir(COMPLIANCE_DIR):
        if f.endswith("_compliance.json") and len(f.split("_")[0]) == 2:
            ufs.append(f.split("_")[0])
    return sorted(ufs)


def consultar_empresa_compliance(cnpj):
    """Busca compliance de uma empresa especifica no cache local.

    Procura em todos os arquivos de compliance por UF.

    Args:
        cnpj: CNPJ da empresa (com ou sem formatacao)

    Returns:
        Dict com dados de compliance ou None
    """
    cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "").strip()

    if not os.path.isdir(COMPLIANCE_DIR):
        return None

    for f in os.listdir(COMPLIANCE_DIR):
        if not f.endswith("_compliance.json"):
            continue
        caminho = os.path.join(COMPLIANCE_DIR, f)
        dados = _carregar_json(caminho)
        if not dados:
            continue
        for emp in dados:
            emp_cnpj = emp.get("cnpj", "").replace(".", "").replace("/", "").replace("-", "")
            if emp_cnpj == cnpj_limpo:
                return emp

    return None


@st.cache_data(ttl=86400)
def carregar_consumidor_gov():
    """Carrega dados do Consumidor.gov.br (CSV pre-processado).

    Returns:
        DataFrame com reclamacoes (pode ser vazio se CSV nao existe)
    """
    csv_path = os.path.join(COMPLIANCE_DIR, "consumidor_gov_reclamacoes.csv")
    if not os.path.exists(csv_path):
        return pd.DataFrame()

    try:
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8", dtype=str, on_bad_lines="skip")
        if df.empty:
            # Tentar latin-1
            df = pd.read_csv(csv_path, sep=";", encoding="latin-1", dtype=str, on_bad_lines="skip")
        return df
    except Exception:
        try:
            df = pd.read_csv(csv_path, sep=",", encoding="utf-8", dtype=str, on_bad_lines="skip")
            return df
        except Exception:
            return pd.DataFrame()


def extrair_empresas_sancionadas(df_compliance):
    """Extrai apenas empresas com sancoes (CEIS ou CNEP) de um DataFrame de compliance.

    Args:
        df_compliance: DataFrame carregado por carregar_compliance_uf

    Returns:
        Lista de dicts com detalhes das sancoes
    """
    if df_compliance.empty:
        return []

    sancionadas = []
    for _, row in df_compliance.iterrows():
        ceis = row.get("ceis", [])
        cnep = row.get("cnep", [])

        if isinstance(ceis, str):
            try:
                ceis = json.loads(ceis)
            except (json.JSONDecodeError, TypeError):
                ceis = []
        if isinstance(cnep, str):
            try:
                cnep = json.loads(cnep)
            except (json.JSONDecodeError, TypeError):
                cnep = []

        if not ceis and not cnep:
            continue

        for sancao in (ceis or []):
            sancionadas.append({
                "cnpj": row.get("cnpj", ""),
                "nome": row.get("nome", ""),
                "tipo": "CEIS",
                "orgao": sancao.get("orgao", ""),
                "tipo_sancao": sancao.get("tipo_sancao", ""),
                "data_inicio": sancao.get("data_inicio", ""),
                "data_fim": sancao.get("data_fim", ""),
                "fundamentacao": sancao.get("fundamentacao", ""),
            })

        for punicao in (cnep or []):
            sancionadas.append({
                "cnpj": row.get("cnpj", ""),
                "nome": row.get("nome", ""),
                "tipo": "CNEP",
                "orgao": punicao.get("orgao", ""),
                "tipo_sancao": punicao.get("tipo_sancao", ""),
                "data_inicio": punicao.get("data_inicio", ""),
                "data_fim": punicao.get("data_fim", ""),
                "valor_multa": punicao.get("valor_multa", 0),
            })

    return sancionadas


def extrair_contratos_pncp(df_compliance):
    """Extrai contratos PNCP de um DataFrame de compliance.

    Args:
        df_compliance: DataFrame carregado por carregar_compliance_uf

    Returns:
        Lista de dicts com detalhes dos contratos
    """
    if df_compliance.empty:
        return []

    contratos = []
    for _, row in df_compliance.iterrows():
        pncp = row.get("pncp_contratos", [])

        if isinstance(pncp, str):
            try:
                pncp = json.loads(pncp)
            except (json.JSONDecodeError, TypeError):
                pncp = []

        if not pncp:
            continue

        for contrato in pncp:
            contratos.append({
                "cnpj": row.get("cnpj", ""),
                "nome": row.get("nome", ""),
                "orgao": contrato.get("orgao", ""),
                "objeto": contrato.get("objeto", ""),
                "valor": contrato.get("valor", 0),
                "data_inicio": contrato.get("data_inicio", ""),
                "data_fim": contrato.get("data_fim", ""),
                "numero": contrato.get("numero", ""),
            })

    return contratos
