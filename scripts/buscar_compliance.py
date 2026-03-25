"""Script para consultar APIs de compliance governamentais.

Consulta 3 fontes para CNPJs de empresas de transporte/logistica:
1. CGU CEIS - Cadastro de Empresas Inidoneas e Suspensas
2. CGU CNEP - Cadastro Nacional de Empresas Punidas
3. PNCP - Portal Nacional de Contratacoes Publicas
4. Consumidor.gov.br - Reclamacoes (download CSV dados abertos)

Requisitos:
    CGU: chave de API gratuita (portaldatransparencia.gov.br/api-de-dados/cadastrar-email)
    PNCP/Consumidor: sem autenticacao

Execucao:
    # Consultar CGU para empresas de uma UF:
    python scripts/buscar_compliance.py --uf SC --api cgu --cgu-api-key SUA_CHAVE

    # Consultar PNCP para empresas de uma UF:
    python scripts/buscar_compliance.py --uf SC --api pncp

    # CNPJs especificos:
    python scripts/buscar_compliance.py --cnpjs 12345678000190,98765432000110 --cgu-api-key CHAVE

    # Baixar dados Consumidor.gov.br:
    python scripts/buscar_compliance.py --consumidor

    # Limitar consultas (para teste):
    python scripts/buscar_compliance.py --uf SC --api cgu --limit 100 --cgu-api-key CHAVE
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta

import requests

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils.constants import CGU_CEIS_URL, CGU_CNEP_URL, PNCP_SEARCH_URL

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "empresas")
UF_DIR = os.path.join(DATA_DIR, "uf")
COMPLIANCE_DIR = os.path.join(DATA_DIR, "compliance")
CACHE_FILE = os.path.join(COMPLIANCE_DIR, "cache_consultas.json")

# Rate limits (segundos entre requests)
CGU_DELAY = 0.7    # 90 req/min
PNCP_DELAY = 2.0   # 30 req/min conservador

# Cache: re-consultar apos N dias
CACHE_DIAS = 30


# ============================================================
# Cache incremental
# ============================================================

def _carregar_cache():
    """Carrega cache de consultas ja realizadas."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _salvar_cache(cache):
    """Salva cache de consultas."""
    os.makedirs(COMPLIANCE_DIR, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, default=str)


def _cache_valido(cache, chave):
    """Verifica se consulta esta no cache e ainda e valida."""
    if chave not in cache:
        return False
    timestamp = cache[chave].get("timestamp", "")
    if not timestamp:
        return False
    try:
        dt = datetime.fromisoformat(timestamp)
        return datetime.now() - dt < timedelta(days=CACHE_DIAS)
    except (ValueError, TypeError):
        return False


# ============================================================
# CGU - CEIS (Empresas Inidoneas e Suspensas)
# ============================================================

def consultar_cgu_ceis(cnpj, api_key):
    """Consulta CEIS - Cadastro de Empresas Inidoneas e Suspensas.

    Args:
        cnpj: CNPJ da empresa (somente numeros)
        api_key: Chave de API do Portal da Transparencia

    Returns:
        Lista de sancoes encontradas (pode ser vazia)
    """
    cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")

    headers = {"chave-api-dados": api_key}
    params = {"codigoSancionado": cnpj_limpo, "pagina": 1}

    try:
        resp = requests.get(CGU_CEIS_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        dados = resp.json()

        sancoes = []
        for item in dados:
            # fundamentacao e uma lista de objetos
            fund_lista = item.get("fundamentacao", [])
            fund_desc = fund_lista[0].get("descricao", "") if fund_lista else ""
            sancao = {
                "orgao": item.get("orgaoSancionador", {}).get("nome", ""),
                "tipo_sancao": item.get("tipoSancao", {}).get("descricaoResumida", ""),
                "data_inicio": item.get("dataInicioSancao", ""),
                "data_fim": item.get("dataFimSancao", ""),
                "fundamentacao": fund_desc,
                "fonte": item.get("fonteSancao", {}).get("nomeExibicao", ""),
            }
            sancoes.append(sancao)
        return sancoes

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("    [RATE LIMIT] CGU CEIS - aguardando 60s...")
            time.sleep(60)
            return consultar_cgu_ceis(cnpj, api_key)
        elif e.response.status_code == 404:
            return []
        else:
            print(f"    [ERRO] CGU CEIS {cnpj}: {e}")
            return []
    except Exception as e:
        print(f"    [ERRO] CGU CEIS {cnpj}: {e}")
        return []


# ============================================================
# CGU - CNEP (Empresas Punidas)
# ============================================================

def consultar_cgu_cnep(cnpj, api_key):
    """Consulta CNEP - Cadastro Nacional de Empresas Punidas.

    Args:
        cnpj: CNPJ da empresa (somente numeros)
        api_key: Chave de API do Portal da Transparencia

    Returns:
        Lista de punicoes encontradas (pode ser vazia)
    """
    cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")

    headers = {"chave-api-dados": api_key}
    params = {"codigoSancionado": cnpj_limpo, "pagina": 1}

    try:
        resp = requests.get(CGU_CNEP_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        dados = resp.json()

        punicoes = []
        for item in dados:
            # fundamentacao e uma lista de objetos
            fund_lista = item.get("fundamentacao", [])
            fund_desc = fund_lista[0].get("descricao", "") if fund_lista else ""
            punicao = {
                "orgao": item.get("orgaoSancionador", {}).get("nome", ""),
                "tipo_sancao": item.get("tipoSancao", {}).get("descricaoResumida", ""),
                "data_inicio": item.get("dataInicioSancao", ""),
                "data_fim": item.get("dataFimSancao", ""),
                "valor_multa": item.get("valorMulta", 0),
                "fundamentacao": fund_desc,
            }
            punicoes.append(punicao)
        return punicoes

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("    [RATE LIMIT] CGU CNEP - aguardando 60s...")
            time.sleep(60)
            return consultar_cgu_cnep(cnpj, api_key)
        elif e.response.status_code == 404:
            return []
        else:
            print(f"    [ERRO] CGU CNEP {cnpj}: {e}")
            return []
    except Exception as e:
        print(f"    [ERRO] CGU CNEP {cnpj}: {e}")
        return []


# ============================================================
# PNCP - Contratos Publicos
# ============================================================

def consultar_pncp_contratos(cnpj):
    """Consulta PNCP - contratos publicos via endpoint de busca.

    Usa /api/search com CNPJ como termo de busca e filtro tipos_documento=contrato.
    A API consulta de contratos (/v1/contratos) nao suporta filtro por fornecedor.

    Args:
        cnpj: CNPJ da empresa (somente numeros)

    Returns:
        Lista de contratos encontrados (pode ser vazia)
    """
    cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")

    url = PNCP_SEARCH_URL
    params = {
        "q": cnpj_limpo,
        "tipos_documento": "contrato",
        "pagina": 1,
        "tam_pagina": 50,
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        dados = resp.json()

        itens = dados.get("items", [])

        contratos = []
        for item in itens:
            contrato = {
                "orgao": item.get("orgao_nome", ""),
                "objeto": item.get("description", item.get("title", "")),
                "valor": item.get("valor_global", 0),
                "data_inicio": item.get("data_inicio_vigencia", ""),
                "data_fim": item.get("data_fim_vigencia", ""),
                "numero": item.get("title", ""),
                "uf": item.get("uf", ""),
                "municipio": item.get("municipio_nome", ""),
            }
            contratos.append(contrato)
        return contratos

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("    [RATE LIMIT] PNCP - aguardando 60s...")
            time.sleep(60)
            return consultar_pncp_contratos(cnpj)
        elif e.response.status_code in (404, 400):
            return []
        else:
            print(f"    [ERRO] PNCP {cnpj}: {e}")
            return []
    except (json.JSONDecodeError, ValueError):
        return []
    except Exception as e:
        print(f"    [ERRO] PNCP {cnpj}: {e}")
        return []


# ============================================================
# Consumidor.gov.br (CSV dados abertos)
# ============================================================

def baixar_consumidor_gov(output_dir):
    """Baixa CSVs publicos do Consumidor.gov.br.

    Os dados abertos estao disponíveis em:
    https://dados.gov.br/dados/conjuntos-dados/reclamacoes-do-consumidor-gov-br

    Baixa o CSV mais recente e filtra por CNAEs de transporte.
    """
    print("\n=== Consumidor.gov.br - Dados Abertos ===")

    # URL da API CKAN do dados.gov.br para listar recursos do dataset
    ckan_url = "https://dados.gov.br/api/3/action/package_show"
    params = {"id": "reclamacoes-do-consumidor-gov-br"}

    try:
        resp = requests.get(ckan_url, params=params, timeout=30)
        resp.raise_for_status()
        dados = resp.json()

        resources = dados.get("result", {}).get("resources", [])
        if not resources:
            print("  [ERRO] Nenhum recurso encontrado no dataset")
            return False

        # Procurar CSV mais recente
        csv_url = None
        for r in reversed(resources):
            url = r.get("url", "")
            fmt = r.get("format", "").upper()
            if fmt == "CSV" or url.lower().endswith(".csv"):
                csv_url = url
                break

        if not csv_url:
            print("  [ERRO] CSV nao encontrado no dataset")
            print("  Recursos disponíveis:")
            for r in resources:
                print(f"    - {r.get('name', '?')} ({r.get('format', '?')}): {r.get('url', '?')}")
            return False

        print(f"  Baixando: {csv_url}")
        os.makedirs(output_dir, exist_ok=True)

        resp = requests.get(csv_url, timeout=120, stream=True)
        resp.raise_for_status()

        csv_path = os.path.join(output_dir, "consumidor_gov_reclamacoes.csv")
        total_bytes = 0
        with open(csv_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                total_bytes += len(chunk)

        size_mb = total_bytes / (1024 * 1024)
        print(f"  [OK] Salvo: {csv_path} ({size_mb:.1f} MB)")
        return True

    except Exception as e:
        print(f"  [ERRO] Consumidor.gov.br: {e}")
        return False


# ============================================================
# Carregar CNPJs de empresas
# ============================================================

def _carregar_cnpjs_uf(uf):
    """Carrega CNPJs e nomes de empresas de uma UF."""
    caminho = os.path.join(UF_DIR, f"{uf}.json")
    if not os.path.exists(caminho):
        print(f"  [ERRO] Arquivo nao encontrado: {caminho}")
        print(f"  Execute primeiro: python scripts/buscar_empresas_transporte.py PROJECT_ID --uf {uf}")
        return []

    with open(caminho, "r", encoding="utf-8") as f:
        dados = json.load(f)

    empresas = []
    for emp in dados:
        cnpj = emp.get("cnpj", "")
        nome = emp.get("nome", "")
        if cnpj:
            empresas.append({"cnpj": cnpj, "nome": nome})

    print(f"  Carregadas {len(empresas):,} empresas de {uf}")
    return empresas


# ============================================================
# Processamento principal
# ============================================================

def processar_compliance(empresas, apis, api_key=None, limit=None):
    """Consulta APIs de compliance para lista de empresas.

    Args:
        empresas: Lista de dicts com 'cnpj' e 'nome'
        apis: Lista de APIs a consultar ('cgu', 'pncp')
        api_key: Chave CGU (obrigatoria se 'cgu' em apis)
        limit: Limitar numero de consultas (para teste)

    Returns:
        Lista de resultados de compliance
    """
    if "cgu" in apis and not api_key:
        print("  [ERRO] API key CGU necessaria. Use --cgu-api-key ou CGU_API_KEY env var.")
        return []

    cache = _carregar_cache()
    resultados = []

    total = min(len(empresas), limit) if limit else len(empresas)
    print(f"\n  Consultando {total:,} empresas | APIs: {', '.join(apis)}")

    consultados = 0
    encontrados_ceis = 0
    encontrados_cnep = 0
    encontrados_pncp = 0

    for i, emp in enumerate(empresas[:total]):
        cnpj = emp["cnpj"]
        nome = emp.get("nome", "")

        resultado = {
            "cnpj": cnpj,
            "nome": nome,
            "ceis": [],
            "cnep": [],
            "pncp_contratos": [],
            "consultado_em": datetime.now().isoformat(),
        }

        # CGU CEIS
        if "cgu" in apis:
            chave_ceis = f"ceis:{cnpj}"
            if _cache_valido(cache, chave_ceis):
                resultado["ceis"] = cache[chave_ceis].get("dados", [])
            else:
                sancoes = consultar_cgu_ceis(cnpj, api_key)
                resultado["ceis"] = sancoes
                cache[chave_ceis] = {
                    "dados": sancoes,
                    "timestamp": datetime.now().isoformat(),
                }
                time.sleep(CGU_DELAY)

            # CGU CNEP
            chave_cnep = f"cnep:{cnpj}"
            if _cache_valido(cache, chave_cnep):
                resultado["cnep"] = cache[chave_cnep].get("dados", [])
            else:
                punicoes = consultar_cgu_cnep(cnpj, api_key)
                resultado["cnep"] = punicoes
                cache[chave_cnep] = {
                    "dados": punicoes,
                    "timestamp": datetime.now().isoformat(),
                }
                time.sleep(CGU_DELAY)

        # PNCP
        if "pncp" in apis:
            chave_pncp = f"pncp:{cnpj}"
            if _cache_valido(cache, chave_pncp):
                resultado["pncp_contratos"] = cache[chave_pncp].get("dados", [])
            else:
                contratos = consultar_pncp_contratos(cnpj)
                resultado["pncp_contratos"] = contratos
                cache[chave_pncp] = {
                    "dados": contratos,
                    "timestamp": datetime.now().isoformat(),
                }
                time.sleep(PNCP_DELAY)

        if resultado["ceis"]:
            encontrados_ceis += 1
        if resultado["cnep"]:
            encontrados_cnep += 1
        if resultado["pncp_contratos"]:
            encontrados_pncp += 1

        consultados += 1
        resultados.append(resultado)

        # Salvar cache periodicamente (a cada 50 empresas)
        if consultados % 50 == 0:
            _salvar_cache(cache)
            print(f"  [{consultados:,}/{total:,}] "
                  f"CEIS={encontrados_ceis} CNEP={encontrados_cnep} PNCP={encontrados_pncp}")

    # Salvar cache final
    _salvar_cache(cache)

    print(f"\n  Concluido: {consultados:,} empresas consultadas")
    print(f"  CEIS: {encontrados_ceis} sancionadas")
    print(f"  CNEP: {encontrados_cnep} punidas")
    print(f"  PNCP: {encontrados_pncp} com contratos")

    return resultados


def salvar_resultados(resultados, uf=None):
    """Salva resultados de compliance em JSON."""
    os.makedirs(COMPLIANCE_DIR, exist_ok=True)

    # Salvar arquivo por UF (ou geral)
    nome_arquivo = f"{uf}_compliance.json" if uf else "compliance.json"
    caminho = os.path.join(COMPLIANCE_DIR, nome_arquivo)

    # Se ja existe, mesclar com resultados anteriores
    existentes = {}
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            dados_existentes = json.load(f)
        for item in dados_existentes:
            existentes[item["cnpj"]] = item

    # Atualizar/adicionar novos resultados
    for item in resultados:
        existentes[item["cnpj"]] = item

    lista_final = list(existentes.values())

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=2, default=str)
    print(f"  [OK] {nome_arquivo} - {len(lista_final)} empresas")

    # Gerar resumo
    _gerar_resumo(lista_final, uf)


def _gerar_resumo(resultados, uf=None):
    """Gera resumo de compliance e salva."""
    total = len(resultados)
    ceis = sum(1 for r in resultados if r.get("ceis"))
    cnep = sum(1 for r in resultados if r.get("cnep"))
    pncp = sum(1 for r in resultados if r.get("pncp_contratos"))

    resumo = {
        "uf": uf or "todas",
        "total_consultados": total,
        "ceis_encontrados": ceis,
        "cnep_encontrados": cnep,
        "pncp_com_contratos": pncp,
        "atualizado_em": datetime.now().strftime("%Y-%m-%d"),
    }

    # Salvar resumo individual
    nome_resumo = f"{uf}_resumo.json" if uf else "resumo_compliance.json"
    caminho_resumo = os.path.join(COMPLIANCE_DIR, nome_resumo)
    with open(caminho_resumo, "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {nome_resumo}")

    # Atualizar resumo geral (todas UFs)
    resumo_geral_path = os.path.join(COMPLIANCE_DIR, "resumo_geral.json")
    resumo_geral = {}
    if os.path.exists(resumo_geral_path):
        with open(resumo_geral_path, "r", encoding="utf-8") as f:
            resumo_geral = json.load(f)

    chave = uf or "geral"
    resumo_geral[chave] = resumo

    with open(resumo_geral_path, "w", encoding="utf-8") as f:
        json.dump(resumo_geral, f, ensure_ascii=False, indent=2)


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Consultar APIs de compliance governamentais para empresas de transporte"
    )
    parser.add_argument(
        "--uf", type=str, default=None,
        help="UF para consultar (usa empresas de data/empresas/uf/{UF}.json)"
    )
    parser.add_argument(
        "--cnpjs", type=str, default=None,
        help="CNPJs separados por virgula (consulta direta)"
    )
    parser.add_argument(
        "--api", type=str, default=None, choices=["cgu", "pncp", "todas"],
        help="API especifica para consultar (padrao: todas)"
    )
    parser.add_argument(
        "--consumidor", action="store_true",
        help="Baixar CSVs do Consumidor.gov.br"
    )
    parser.add_argument(
        "--cgu-api-key", type=str, default=None,
        help="Chave de API do Portal da Transparencia CGU"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limitar numero de empresas consultadas (para teste)"
    )
    args = parser.parse_args()

    print(f"=== Compliance Empresarial - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    print(f"Diretorio de dados: {os.path.abspath(COMPLIANCE_DIR)}")

    # Modo consumidor.gov.br
    if args.consumidor:
        baixar_consumidor_gov(COMPLIANCE_DIR)
        print(f"\n=== Concluido - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
        return

    # Resolver API key CGU
    api_key = args.cgu_api_key or os.environ.get("CGU_API_KEY")

    # Carregar arquivo .env se existir
    if not api_key:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("CGU_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    # Determinar APIs a consultar
    if args.api == "cgu":
        apis = ["cgu"]
    elif args.api == "pncp":
        apis = ["pncp"]
    else:
        apis = ["cgu", "pncp"]

    # Carregar empresas
    empresas = []

    if args.cnpjs:
        # CNPJs diretos
        for cnpj in args.cnpjs.split(","):
            cnpj = cnpj.strip()
            if cnpj:
                empresas.append({"cnpj": cnpj, "nome": ""})
        print(f"\n  {len(empresas)} CNPJs fornecidos diretamente")
    elif args.uf:
        uf = args.uf.upper()
        empresas = _carregar_cnpjs_uf(uf)
    else:
        print("\n  [ERRO] Informe --uf, --cnpjs ou --consumidor")
        parser.print_help()
        return

    if not empresas:
        print("  [ERRO] Nenhuma empresa para consultar")
        return

    # Processar
    resultados = processar_compliance(
        empresas, apis, api_key=api_key, limit=args.limit
    )

    if resultados:
        uf = args.uf.upper() if args.uf else None
        salvar_resultados(resultados, uf=uf)

    print(f"\n=== Concluido - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")


if __name__ == "__main__":
    main()
