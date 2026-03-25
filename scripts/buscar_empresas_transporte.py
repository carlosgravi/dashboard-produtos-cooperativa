"""Script para buscar empresas de transporte/logística/correios via BigQuery.

Usa a biblioteca basedosdados para consultar a Receita Federal (CNPJ) no BigQuery,
filtrando apenas empresas com CNAEs específicos de transporte/logística/correios.

Requisitos:
    pip install pandas-gbq
    gcloud auth application-default login

Execução:
    # Modo agregado (resumo por município - padrão):
    python scripts/buscar_empresas_transporte.py <PROJECT_ID>

    # Modo individual por UF (empresas com endereço completo):
    python scripts/buscar_empresas_transporte.py <PROJECT_ID> --uf SC

    # Incluir RNTRC no modo agregado (opcional):
    python scripts/buscar_empresas_transporte.py <PROJECT_ID> --com-rntrc
"""

import argparse
import gzip
import json
import os
import sys
import time
from datetime import datetime

import pandas as pd

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils.constants import (
    CNAES_TRANSPORTE,
    CATEGORIAS_EMPRESAS,
    ANTT_TRANSPORTADORES_CKAN,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "empresas")
UF_DIR = os.path.join(DATA_DIR, "uf")


def _salvar_json(arquivo, dados, diretorio=None):
    """Salva dados como JSON."""
    diretorio = diretorio or DATA_DIR
    os.makedirs(diretorio, exist_ok=True)
    caminho = os.path.join(diretorio, arquivo)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, default=str)
    n = len(dados) if isinstance(dados, (list, dict)) else 0
    print(f"  [OK] {arquivo} - {n} registros")


def _cnae_para_categoria(cnae):
    """Retorna a categoria de um CNAE."""
    for categoria, cnaes in CATEGORIAS_EMPRESAS.items():
        if cnae in cnaes:
            return categoria
    return "Outros"


# ============================================================
# 1. BigQuery - Receita Federal (Base dos Dados) - AGREGADO
# ============================================================

def buscar_empresas_bigquery(project_id):
    """Busca empresas de transporte/logística/correios via BigQuery.

    Retorna dados AGREGADOS por município + CNAE.
    IMPORTANTE: agrega ANTES do JOIN com municípios para evitar
    multiplicação de linhas (tabela de municípios pode ter duplicatas).
    """
    print("\n=== BigQuery - Receita Federal (Base dos Dados) ===")

    if not project_id:
        print("  [ERRO] Project ID do Google Cloud não informado.")
        return pd.DataFrame()

    try:
        import pandas_gbq
    except ImportError:
        print("  [ERRO] Instale pandas-gbq: pip install pandas-gbq")
        return pd.DataFrame()

    cnaes_lista = list(CNAES_TRANSPORTE.keys())
    cnaes_str = ", ".join(f"'{c}'" for c in cnaes_lista)

    # Filtrar pela data mais recente (tabela tem snapshots mensais!)
    # e agregar ANTES do JOIN para evitar multiplicação
    query = f"""
    WITH ultima_data AS (
        SELECT MAX(data) AS data_max
        FROM `basedosdados.br_me_cnpj.estabelecimentos`
    ),
    agregado AS (
        SELECT
            e.id_municipio,
            e.sigla_uf AS uf,
            e.cnae_fiscal_principal AS cnae,
            COUNT(*) AS total
        FROM `basedosdados.br_me_cnpj.estabelecimentos` e
        CROSS JOIN ultima_data ud
        WHERE e.cnae_fiscal_principal IN ({cnaes_str})
          AND e.situacao_cadastral = '2'
          AND e.data = ud.data_max
        GROUP BY e.id_municipio, e.sigla_uf, e.cnae_fiscal_principal
    ),
    mun AS (
        SELECT DISTINCT id_municipio, nome
        FROM `basedosdados.br_bd_diretorios_brasil.municipio`
    )
    SELECT
        COALESCE(mun.nome, 'Desconhecido') AS municipio,
        a.uf,
        a.cnae,
        a.total
    FROM agregado a
    LEFT JOIN mun ON SAFE_CAST(a.id_municipio AS STRING) = mun.id_municipio
    ORDER BY a.total DESC
    """

    print(f"  Project ID: {project_id}")
    print("  Executando query BigQuery (agregada por município/CNAE)...")
    print("  (Na primeira vez, abre o browser para autenticação Google)")
    inicio = time.time()

    try:
        df = pandas_gbq.read_gbq(query, project_id=project_id)
        elapsed = time.time() - inicio
        total = int(df["total"].sum()) if not df.empty else 0
        print(f"  Query concluída em {elapsed:.0f}s - {len(df)} linhas, {total:,} empresas")

        if df.empty:
            return df

        # Adicionar descrição do CNAE e categoria
        df["cnae_desc"] = df["cnae"].map(CNAES_TRANSPORTE).fillna("Outros")
        df["categoria"] = df["cnae"].apply(_cnae_para_categoria)
        df["fonte"] = "RFB"

        return df

    except Exception as e:
        print(f"  [ERRO] BigQuery: {e}")
        return pd.DataFrame()


# ============================================================
# 1b. BigQuery - Receita Federal - INDIVIDUAL por UF
# ============================================================

def buscar_empresas_bigquery_uf(project_id, uf):
    """Busca empresas individuais com endereço completo para uma UF.

    Usa SELECT DISTINCT para municípios e evita duplicação.
    Retorna linhas individuais com CNPJ, razão social, endereço, etc.
    """
    print(f"\n=== BigQuery - Empresas individuais para {uf} ===")

    if not project_id:
        print("  [ERRO] Project ID não informado.")
        return pd.DataFrame()

    try:
        import pandas_gbq
    except ImportError:
        print("  [ERRO] Instale pandas-gbq: pip install pandas-gbq")
        return pd.DataFrame()

    cnaes_lista = list(CNAES_TRANSPORTE.keys())
    cnaes_str = ", ".join(f"'{c}'" for c in cnaes_lista)

    # Filtrar pela data mais recente (tabela tem snapshots mensais!)
    # razao_social fica na tabela 'empresas', ligada por cnpj_basico
    query = f"""
    WITH ultima_data AS (
        SELECT MAX(data) AS data_max
        FROM `basedosdados.br_me_cnpj.estabelecimentos`
    ),
    emp_recente AS (
        SELECT cnpj_basico, razao_social, porte, natureza_juridica, capital_social
        FROM `basedosdados.br_me_cnpj.empresas`
        WHERE data = (SELECT MAX(data) FROM `basedosdados.br_me_cnpj.empresas`)
    ),
    mun AS (
        SELECT DISTINCT id_municipio, nome
        FROM `basedosdados.br_bd_diretorios_brasil.municipio`
    )
    SELECT
        e.cnpj,
        COALESCE(emp_recente.razao_social, e.nome_fantasia, '') AS razao_social,
        e.nome_fantasia,
        e.cnae_fiscal_principal AS cnae,
        e.tipo_logradouro,
        e.logradouro,
        e.numero,
        e.bairro,
        e.cep,
        e.ddd_1,
        e.telefone_1,
        e.ddd_2,
        e.telefone_2,
        e.email,
        COALESCE(mun.nome, 'Desconhecido') AS municipio,
        e.sigla_uf AS uf,
        emp_recente.porte,
        emp_recente.natureza_juridica,
        SAFE_CAST(emp_recente.capital_social AS FLOAT64) AS capital_social
    FROM `basedosdados.br_me_cnpj.estabelecimentos` e
    CROSS JOIN ultima_data ud
    LEFT JOIN emp_recente ON e.cnpj_basico = emp_recente.cnpj_basico
    LEFT JOIN mun ON SAFE_CAST(e.id_municipio AS STRING) = mun.id_municipio
    WHERE e.cnae_fiscal_principal IN ({cnaes_str})
      AND e.situacao_cadastral = '2'
      AND e.data = ud.data_max
      AND e.sigla_uf = '{uf}'
    ORDER BY razao_social
    """

    print(f"  Project ID: {project_id}")
    print(f"  Buscando empresas individuais em {uf} (somente CNAEs transporte/logística)...")
    inicio = time.time()

    try:
        df = pandas_gbq.read_gbq(query, project_id=project_id)
        elapsed = time.time() - inicio
        print(f"  Query concluída em {elapsed:.0f}s - {len(df)} empresas")

        if df.empty:
            return df

        # Montar endereço completo
        df["tipo_logradouro"] = df["tipo_logradouro"].fillna("")
        df["logradouro"] = df["logradouro"].fillna("")
        df["numero"] = df["numero"].fillna("")
        df["bairro"] = df["bairro"].fillna("")

        def _montar_endereco(row):
            partes = []
            tipo = str(row["tipo_logradouro"]).strip()
            logr = str(row["logradouro"]).strip()
            if tipo and logr:
                partes.append(f"{tipo} {logr}")
            elif logr:
                partes.append(logr)
            num = str(row["numero"]).strip()
            if num and num.lower() not in ("nan", "none", ""):
                partes.append(num)
            bairro = str(row["bairro"]).strip()
            if bairro and bairro.lower() not in ("nan", "none", ""):
                partes.append(bairro)
            return ", ".join(partes) if partes else ""

        df["endereco"] = df.apply(_montar_endereco, axis=1)

        # Montar telefone: "(DDD) NUMERO"
        def _montar_telefone(row):
            fones = []
            for i in ("1", "2"):
                ddd = str(row.get(f"ddd_{i}", "")).strip()
                tel = str(row.get(f"telefone_{i}", "")).strip()
                if tel and tel.lower() not in ("nan", "none", ""):
                    if ddd and ddd.lower() not in ("nan", "none", ""):
                        fones.append(f"({ddd}) {tel}")
                    else:
                        fones.append(tel)
            return " / ".join(fones) if fones else ""

        df["telefone"] = df.apply(_montar_telefone, axis=1)

        # Limpar email
        df["email"] = df["email"].fillna("").astype(str).str.strip()
        df["email"] = df["email"].apply(lambda x: "" if x.lower() in ("nan", "none") else x)

        # Limpar nome fantasia
        df["nome_fantasia"] = df["nome_fantasia"].fillna("").astype(str).str.strip()
        df["nome_fantasia"] = df["nome_fantasia"].apply(lambda x: "" if x.lower() in ("nan", "none") else x)

        # Adicionar metadados
        df["cnae_desc"] = df["cnae"].map(CNAES_TRANSPORTE).fillna("Outros")
        df["categoria"] = df["cnae"].apply(_cnae_para_categoria)
        df["fonte"] = "RFB"

        # Mapear porte e natureza jurídica
        portes = {"1": "Micro Empresa", "3": "Pequeno Porte", "5": "Demais", "0": "Não informado"}
        nat_juridicas = {
            "2135": "MEI", "2062": "Ltda", "2054": "S.A.",
            "2046": "S.A. Aberta", "2143": "Cooperativa",
            "2070": "Assoc. Privada", "2127": "EIRELI",
        }
        df["porte_desc"] = df["porte"].astype(str).map(portes).fillna("Outro")
        df["nat_juridica_desc"] = df["natureza_juridica"].astype(str).map(nat_juridicas).fillna("Outro")

        # Normalizar CEP
        df["cep"] = df["cep"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(8)

        # Coordenadas (serão preenchidas pelo geocodificador)
        df["lat"] = None
        df["lon"] = None

        # Renomear
        df = df.rename(columns={"razao_social": "nome"})

        # Colunas finais
        colunas = ["cnpj", "nome", "nome_fantasia", "cnae", "cnae_desc", "categoria",
                    "endereco", "cep", "municipio", "uf",
                    "telefone", "email",
                    "porte", "porte_desc", "natureza_juridica", "nat_juridica_desc", "capital_social",
                    "lat", "lon", "fonte"]
        colunas = [c for c in colunas if c in df.columns]
        return df[colunas]

    except Exception as e:
        print(f"  [ERRO] BigQuery UF {uf}: {e}")
        return pd.DataFrame()


# ============================================================
# 2. RNTRC - Transportadores ANTT (opcional, modo agregado)
# ============================================================

def buscar_transportadores_rntrc():
    """Processa CSV de transportadores RNTRC extraindo CEP, município, UF.

    ATENÇÃO: RNTRC não tem filtro por CNAE - inclui TODOS os transportadores.
    Use apenas se quiser dados complementares ao RFB.
    """
    print("\n=== RNTRC - Transportadores ANTT ===")

    import requests

    try:
        resp = requests.get(ANTT_TRANSPORTADORES_CKAN, timeout=30)
        resp.raise_for_status()
        dados = resp.json()
        resources = dados.get("result", {}).get("resources", [])
        url_csv = None
        for r in reversed(resources):
            url = r.get("url", "")
            if "transportadores" in url.lower() and url.endswith(".csv"):
                url_csv = url
                break
        if not url_csv:
            print("  [ERRO] URL de transportadores não encontrada via CKAN")
            return pd.DataFrame()
    except Exception as e:
        print(f"  [ERRO] CKAN: {e}")
        return pd.DataFrame()

    print(f"  Baixando CSV de transportadores (chunks)...")
    inicio = time.time()

    try:
        chunks = pd.read_csv(
            url_csv, sep=";", encoding="latin-1", dtype=str,
            chunksize=50000, on_bad_lines="skip",
        )

        frames = []
        total_rows = 0
        for chunk in chunks:
            chunk.columns = [c.strip().lower() for c in chunk.columns]

            col_uf = next((c for c in chunk.columns if c == "uf"), None)
            col_mun = next((c for c in chunk.columns if "municipio" in c), None)
            col_cep = next((c for c in chunk.columns if "cep" in c), None)
            col_cat = next((c for c in chunk.columns if "categoria" in c), None)
            col_sit = next((c for c in chunk.columns if "situacao" in c), None)
            col_razao = next((c for c in chunk.columns if "razao" in c or "nome" in c), None)
            col_cnpj = next((c for c in chunk.columns if "cnpj" in c or "cpf" in c), None)

            if not col_uf:
                continue

            renames = {col_uf: "uf"}
            if col_mun:
                renames[col_mun] = "municipio"
            if col_cep:
                renames[col_cep] = "cep"
            if col_cat:
                renames[col_cat] = "categoria_rntrc"
            if col_sit:
                renames[col_sit] = "situacao"
            if col_razao:
                renames[col_razao] = "nome"
            if col_cnpj:
                renames[col_cnpj] = "cnpj"

            chunk = chunk.rename(columns=renames)

            if "situacao" in chunk.columns:
                mask = chunk["situacao"].str.upper().str.contains("ATIV", na=False)
                chunk = chunk[mask]

            total_rows += len(chunk)
            cols_disponiveis = [c for c in ["cnpj", "nome", "uf", "municipio", "cep", "categoria_rntrc"] if c in chunk.columns]
            frames.append(chunk[cols_disponiveis])

        if not frames:
            print("  [VAZIO] Nenhum transportador processado")
            return pd.DataFrame()

        df = pd.concat(frames, ignore_index=True)
        elapsed = time.time() - inicio
        print(f"  Processados {total_rows} transportadores em {elapsed:.0f}s")

        df["cnae"] = "4930202"
        df["cnae_desc"] = CNAES_TRANSPORTE.get("4930202", "Transporte de cargas")
        df["categoria"] = "Transporte de Cargas"
        df["fonte"] = "RNTRC"

        if "cep" in df.columns:
            df["cep"] = df["cep"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(8)

        return df

    except Exception as e:
        print(f"  [ERRO] RNTRC: {e}")
        return pd.DataFrame()


# ============================================================
# 3. Combinar e gerar resumos (modo agregado)
# ============================================================

def _agregar_rntrc(df_rntrc):
    """Agrega dados individuais do RNTRC por município + UF + CNAE."""
    if df_rntrc.empty:
        return pd.DataFrame()

    cols_group = []
    if "municipio" in df_rntrc.columns:
        cols_group.append("municipio")
    if "uf" in df_rntrc.columns:
        cols_group.append("uf")
    cols_group.append("cnae")

    df_agg = df_rntrc.groupby(cols_group).size().reset_index(name="total")
    df_agg["cnae_desc"] = df_agg["cnae"].map(CNAES_TRANSPORTE).fillna("Outros")
    df_agg["categoria"] = df_agg["cnae"].apply(_cnae_para_categoria)
    df_agg["fonte"] = "RNTRC"
    return df_agg


def combinar_e_salvar(df_rfb, df_rntrc=None):
    """Combina dados agregados RFB (+ opcionalmente RNTRC) e gera resumos."""
    print("\n=== Combinando dados ===")

    df_rntrc_agg = _agregar_rntrc(df_rntrc) if df_rntrc is not None else pd.DataFrame()

    frames = []
    if not df_rfb.empty:
        total_rfb = int(df_rfb["total"].sum())
        print(f"  RFB: {total_rfb:,} empresas ({len(df_rfb)} linhas agregadas)")
        frames.append(df_rfb)
    if not df_rntrc_agg.empty:
        total_rntrc = int(df_rntrc_agg["total"].sum())
        print(f"  RNTRC: {total_rntrc:,} transportadores ({len(df_rntrc_agg)} linhas agregadas)")
        frames.append(df_rntrc_agg)

    if not frames:
        print("  [ERRO] Nenhum dado para combinar")
        return

    df = pd.concat(frames, ignore_index=True)
    total_geral = int(df["total"].sum())
    print(f"  Total combinado: {total_geral:,} empresas")

    # === Resumo por UF ===
    resumo_uf = df.groupby("uf")["total"].sum().reset_index()

    for cat in CATEGORIAS_EMPRESAS:
        mask = df["categoria"] == cat
        cat_col = cat.lower().replace(" ", "_").replace("ã", "a").replace("í", "i")
        por_cat = df[mask].groupby("uf")["total"].sum().reset_index(name=cat_col)
        resumo_uf = resumo_uf.merge(por_cat, on="uf", how="left")

    for fonte in ["RFB", "RNTRC"]:
        mask = df["fonte"] == fonte
        if mask.any():
            por_fonte = df[mask].groupby("uf")["total"].sum().reset_index(name=f"fonte_{fonte.lower()}")
            resumo_uf = resumo_uf.merge(por_fonte, on="uf", how="left")

    resumo_uf = resumo_uf.fillna(0)
    for col in resumo_uf.columns:
        if col != "uf":
            resumo_uf[col] = resumo_uf[col].astype(int)
    resumo_uf = resumo_uf.sort_values("total", ascending=False)
    _salvar_json("resumo_por_uf.json", resumo_uf.to_dict(orient="records"))

    # === Resumo por CNAE ===
    resumo_cnae = df.groupby(["cnae", "cnae_desc", "categoria"])["total"].sum().reset_index()
    resumo_cnae = resumo_cnae.sort_values("total", ascending=False)
    _salvar_json("resumo_por_cnae.json", resumo_cnae.to_dict(orient="records"))

    # === Resumo por município ===
    cols_group = ["municipio", "uf"] if "municipio" in df.columns else ["uf"]
    resumo_mun = df.groupby(cols_group)["total"].sum().reset_index()

    if "municipio" in df.columns:
        for cat in CATEGORIAS_EMPRESAS:
            mask = df["categoria"] == cat
            cat_col = cat.lower().replace(" ", "_").replace("ã", "a").replace("í", "i")
            por_cat = df[mask].groupby(cols_group)["total"].sum().reset_index(name=cat_col)
            resumo_mun = resumo_mun.merge(por_cat, on=cols_group, how="left")

        for fonte in ["RFB", "RNTRC"]:
            mask = df["fonte"] == fonte
            if mask.any():
                por_fonte = df[mask].groupby(cols_group)["total"].sum().reset_index(name=f"fonte_{fonte.lower()}")
                resumo_mun = resumo_mun.merge(por_fonte, on=cols_group, how="left")

    resumo_mun = resumo_mun.fillna(0)
    for col in resumo_mun.columns:
        if col not in cols_group:
            resumo_mun[col] = resumo_mun[col].astype(int)
    resumo_mun = resumo_mun.sort_values("total", ascending=False)
    _salvar_json("resumo_por_municipio.json", resumo_mun.to_dict(orient="records"))

    print(f"\n  Resumos gerados:")
    print(f"    UFs: {len(resumo_uf)}")
    print(f"    CNAEs: {len(resumo_cnae)}")
    print(f"    Municípios: {len(resumo_mun)}")


# ============================================================
# 4. Modo individual por UF (somente RFB)
# ============================================================

def salvar_uf(project_id, uf):
    """Busca empresas individuais RFB para uma UF e salva.

    Somente RFB (filtrado por CNAE). RNTRC não é incluído
    pois não possui filtro por CNAE nem endereço completo.
    """
    print(f"\n=== Modo individual: {uf} ===")

    df = buscar_empresas_bigquery_uf(project_id, uf)

    if df.empty:
        print(f"  [ERRO] Nenhum dado para {uf}")
        return

    # Deduplicar por CNPJ (caso haja duplicatas)
    if "cnpj" in df.columns:
        antes = len(df)
        df = df.drop_duplicates(subset=["cnpj"], keep="first")
        depois = len(df)
        if antes != depois:
            print(f"  Deduplicado por CNPJ: {antes} -> {depois}")

    print(f"  Total {uf}: {len(df):,} empresas")

    registros = df.to_dict(orient="records")

    # Salvar como .json.gz (comprimido) para caber no GitHub
    os.makedirs(UF_DIR, exist_ok=True)
    caminho_gz = os.path.join(UF_DIR, f"{uf}.json.gz")
    with gzip.open(caminho_gz, "wt", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, default=str)
    tamanho_mb = os.path.getsize(caminho_gz) / 1024 / 1024
    print(f"  [OK] {uf}.json.gz - {len(registros)} registros ({tamanho_mb:.1f} MB)")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Buscar empresas de transporte/logística/correios (RFB via BigQuery)"
    )
    parser.add_argument(
        "project_id", nargs="?", default=None,
        help="Project ID do Google Cloud para BigQuery"
    )
    parser.add_argument(
        "--uf", type=str, default=None,
        help="UF para busca individual (ex: SC). Sem este flag, faz busca agregada."
    )
    parser.add_argument(
        "--com-rntrc", action="store_true",
        help="Incluir dados RNTRC no modo agregado (RNTRC não tem filtro CNAE)."
    )
    args = parser.parse_args()

    project_id = args.project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")

    print(f"=== Busca de Empresas de Transporte - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    print(f"Diretório de dados: {os.path.abspath(DATA_DIR)}")

    if not project_id:
        print("\n  AVISO: Project ID não informado. A busca BigQuery será ignorada.")
        print("  Para incluir dados da Receita Federal, use:")
        print("    python scripts/buscar_empresas_transporte.py <PROJECT_ID>")
        print("    ou: set GOOGLE_CLOUD_PROJECT=seu-project-id\n")

    if args.uf:
        # Modo individual: somente RFB com endereço para UF específica
        uf = args.uf.upper()
        print(f"\nModo: individual para UF={uf} (somente RFB com CNAEs específicos)")
        salvar_uf(project_id, uf)
    else:
        # Modo agregado
        print("\nModo: agregado (resumo por município)")
        df_rfb = buscar_empresas_bigquery(project_id)

        df_rntrc = None
        if args.com_rntrc:
            df_rntrc = buscar_transportadores_rntrc()
        else:
            print("\n  RNTRC não incluído (use --com-rntrc para incluir)")

        combinar_e_salvar(df_rfb, df_rntrc)

    print(f"\n=== Concluído - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")


if __name__ == "__main__":
    main()
