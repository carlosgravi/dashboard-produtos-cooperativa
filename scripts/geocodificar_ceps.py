"""Script para geocodificar empresas com coordenadas precisas.

Estratégia de geocodificação (do mais preciso ao menos preciso):
1. Nominatim (OpenStreetMap) - endereço completo -> precisão de edifício
2. AwesomeAPI CEP - CEP -> precisão de trecho de rua
3. IBGE município - centroide do município -> fallback

Modos:
    # Modo município (padrão): enriquece resumo_por_municipio.json com IBGE
    python scripts/geocodificar_ceps.py

    # Modo UF: geocodifica endereços individuais em data/empresas/uf/{UF}.json
    python scripts/geocodificar_ceps.py --uf SC
"""

import argparse
import json
import os
import sys
import time
import unicodedata
from datetime import datetime

import pandas as pd
import requests

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils.constants import (
    IBGE_MUNICIPIOS_URL,
    AWESOMEAPI_CEP_URL,
    NOMINATIM_SEARCH_URL,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "empresas")
UF_DIR = os.path.join(DATA_DIR, "uf")
MUNICIPIOS_FILE = os.path.join(DATA_DIR, "municipios_ibge.csv")
GEOCODE_CACHE_FILE = os.path.join(DATA_DIR, "geocode_cache.json")

# User-Agent obrigatório para Nominatim
NOMINATIM_HEADERS = {"User-Agent": "DashboardTranspocred/1.0 (dashboard cooperativa)"}


def _salvar_json(arquivo, dados, diretorio=None):
    """Salva dados como JSON."""
    diretorio = diretorio or DATA_DIR
    os.makedirs(diretorio, exist_ok=True)
    caminho = os.path.join(diretorio, arquivo)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, default=str)
    n = len(dados) if isinstance(dados, (list, dict)) else 0
    print(f"  [OK] {arquivo} - {n} registros")


def _normalizar(texto):
    """Remove acentos e converte para maiúsculas para comparação."""
    if not texto or not isinstance(texto, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.strip().upper()


# ============================================================
# 1. Baixar dados IBGE de municípios (fallback)
# ============================================================

def baixar_municipios_ibge():
    """Baixa coordenadas dos municípios brasileiros do GitHub."""
    if os.path.exists(MUNICIPIOS_FILE):
        print("  Municípios IBGE já baixados")
        return pd.read_csv(MUNICIPIOS_FILE)

    print("  Baixando coordenadas dos municípios (IBGE)...")
    try:
        df = pd.read_csv(IBGE_MUNICIPIOS_URL)
        os.makedirs(DATA_DIR, exist_ok=True)
        df.to_csv(MUNICIPIOS_FILE, index=False)
        print(f"  [OK] {len(df)} municípios baixados")
        return df
    except Exception as e:
        print(f"  [ERRO] Municípios IBGE: {e}")
        return pd.DataFrame()


def _construir_lookup_ibge(df_municipios):
    """Constrói lookup normalizado de município -> lat/lon."""
    col_nome = next((c for c in df_municipios.columns if "nome" in c.lower()), None)
    col_lat = next((c for c in df_municipios.columns if "lat" in c.lower()), None)
    col_lon = next((c for c in df_municipios.columns if "lon" in c.lower()), None)

    if not all([col_nome, col_lat, col_lon]):
        print(f"  [AVISO] Colunas IBGE: nome={col_nome}, lat={col_lat}, lon={col_lon}")
        return {}

    lookup = {}
    for _, row in df_municipios.iterrows():
        nome = _normalizar(str(row[col_nome]))
        try:
            lat = float(row[col_lat])
            lon = float(row[col_lon])
            lookup[nome] = {"lat": lat, "lon": lon}
        except (ValueError, TypeError):
            continue

    print(f"  Lookup IBGE construído: {len(lookup)} municípios")
    return lookup


# ============================================================
# 2. Enriquecer resumo_por_municipio.json (modo município)
# ============================================================

def enriquecer_municipios(lookup):
    """Adiciona lat/lon ao resumo_por_municipio.json usando lookup IBGE."""
    caminho = os.path.join(DATA_DIR, "resumo_por_municipio.json")
    if not os.path.exists(caminho):
        print("  [ERRO] resumo_por_municipio.json não encontrado")
        return

    with open(caminho, "r", encoding="utf-8") as f:
        resumo = json.load(f)

    print(f"  Municípios no resumo: {len(resumo)}")

    enriquecidos = 0
    sem_match = []
    for r in resumo:
        mun = _normalizar(str(r.get("municipio", "")))
        if mun in lookup:
            r["lat"] = lookup[mun]["lat"]
            r["lon"] = lookup[mun]["lon"]
            enriquecidos += 1
        else:
            sem_match.append(r.get("municipio", "?"))

    _salvar_json("resumo_por_municipio.json", resumo)

    pct = enriquecidos / len(resumo) * 100 if resumo else 0
    print(f"  Municípios com coordenadas: {enriquecidos}/{len(resumo)} ({pct:.1f}%)")

    if sem_match:
        n_show = min(20, len(sem_match))
        print(f"  Sem match ({len(sem_match)} total), primeiros {n_show}:")
        for m in sem_match[:n_show]:
            print(f"    - {m}")


# ============================================================
# 3. Geocodificação individual (modo UF)
# ============================================================

def _carregar_cache():
    """Carrega cache de geocodificação (endereço/CEP -> lat/lon)."""
    if os.path.exists(GEOCODE_CACHE_FILE):
        with open(GEOCODE_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _salvar_cache(cache):
    """Salva cache de geocodificação."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(GEOCODE_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def _geocodificar_nominatim(endereco, municipio, uf):
    """Geocodifica endereço completo via Nominatim (OpenStreetMap).

    Precisão: nível de edifício/número.
    Rate limit: 1 req/s (obrigatório pela política do Nominatim).
    """
    query = f"{endereco}, {municipio}, {uf}, Brasil"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "br",
    }
    try:
        resp = requests.get(
            NOMINATIM_SEARCH_URL, params=params,
            headers=NOMINATIM_HEADERS, timeout=10,
        )
        if resp.status_code == 200:
            results = resp.json()
            if results:
                return {
                    "lat": float(results[0]["lat"]),
                    "lon": float(results[0]["lon"]),
                    "fonte_geo": "nominatim",
                }
    except Exception:
        pass
    return None


def _geocodificar_cep_awesomeapi(cep):
    """Geocodifica CEP via AwesomeAPI. Precisão: trecho de rua."""
    url = AWESOMEAPI_CEP_URL.format(cep=cep)
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            lat = data.get("lat")
            lon = data.get("lng")
            if lat and lon:
                return {
                    "lat": float(lat),
                    "lon": float(lon),
                    "fonte_geo": "cep",
                }
    except Exception:
        pass
    return None


def geocodificar_uf(uf, lookup_ibge=None):
    """Geocodifica empresas individuais em data/empresas/uf/{UF}.json.

    Estratégia por empresa:
    1. Cache (endereço ou CEP já geocodificado anteriormente)
    2. Nominatim com endereço completo (1 req/s) -> precisão edifício
    3. AwesomeAPI com CEP (4 req/s) -> precisão rua
    4. IBGE centroide do município -> fallback

    Agrupa por endereço/CEP únicos para minimizar chamadas API.
    """
    caminho = os.path.join(UF_DIR, f"{uf}.json")
    if not os.path.exists(caminho):
        print(f"  [ERRO] {uf}.json não encontrado em {UF_DIR}")
        print(f"  Execute: python scripts/buscar_empresas_transporte.py <PROJECT_ID> --uf {uf}")
        return

    with open(caminho, "r", encoding="utf-8") as f:
        empresas = json.load(f)

    print(f"\n=== Geocodificação para {uf} ===")
    print(f"  Empresas: {len(empresas):,}")

    cache = _carregar_cache()

    # Agrupar por endereço único para minimizar chamadas
    # Chave: "endereco|municipio|uf" para Nominatim, "cep" para AwesomeAPI
    enderecos_unicos = {}  # chave_endereco -> [indices]
    ceps_unicos = {}       # cep -> [indices]
    ja_tem_coord = 0

    for i, emp in enumerate(empresas):
        lat = emp.get("lat")
        if lat is not None and lat != "" and lat != "None":
            ja_tem_coord += 1
            continue

        endereco = str(emp.get("endereco", "")).strip()
        municipio = str(emp.get("municipio", "")).strip()
        cep = str(emp.get("cep", "")).strip()

        if endereco and municipio:
            chave = f"addr:{endereco}|{municipio}|{uf}"
            enderecos_unicos.setdefault(chave, []).append(i)

        if cep and len(cep) == 8 and cep != "00000000":
            ceps_unicos.setdefault(cep, []).append(i)

    print(f"  Já com coordenadas: {ja_tem_coord:,}")
    print(f"  Endereços únicos: {len(enderecos_unicos):,}")
    print(f"  CEPs únicos: {len(ceps_unicos):,}")

    # Separar o que já está no cache
    enderecos_no_cache = {k: v for k, v in enderecos_unicos.items() if k in cache}
    enderecos_novos = {k: v for k, v in enderecos_unicos.items() if k not in cache}
    ceps_no_cache = {k: v for k, v in ceps_unicos.items() if k in cache}
    ceps_novos = {k: v for k, v in ceps_unicos.items() if k not in cache}

    print(f"  Endereços no cache: {len(enderecos_no_cache):,}")
    print(f"  Endereços novos (Nominatim): {len(enderecos_novos):,}")
    print(f"  CEPs no cache: {len(ceps_no_cache):,}")
    print(f"  CEPs novos (AwesomeAPI): {len(ceps_novos):,}")

    # === Fase 1: Nominatim para endereços novos (1 req/s) ===
    if enderecos_novos:
        total_nom = len(enderecos_novos)
        print(f"\n  [Nominatim] Geocodificando {total_nom:,} endereços (1 req/s)...")
        print(f"  Estimativa: ~{total_nom / 60:.0f} min")

        sucesso_nom = 0
        falha_nom = 0

        for i, (chave, indices) in enumerate(enderecos_novos.items()):
            # Extrair componentes da chave
            _, resto = chave.split(":", 1)
            partes = resto.split("|")
            endereco = partes[0] if len(partes) > 0 else ""
            municipio = partes[1] if len(partes) > 1 else ""

            resultado = _geocodificar_nominatim(endereco, municipio, uf)
            if resultado:
                cache[chave] = resultado
                sucesso_nom += 1
            else:
                cache[chave] = None  # Marcar como tentado
                falha_nom += 1

            # Nominatim: 1 req/s obrigatório
            time.sleep(1.0)

            if (i + 1) % 200 == 0:
                _salvar_cache(cache)
                print(f"    Nominatim: {i + 1}/{total_nom} (OK: {sucesso_nom}, falha: {falha_nom})")

        _salvar_cache(cache)
        print(f"  Nominatim concluído: {sucesso_nom} OK, {falha_nom} falhas")

    # === Fase 2: AwesomeAPI para CEPs novos (4 req/s) ===
    # Só geocodifica CEPs cujas empresas NÃO foram resolvidas pelo Nominatim
    ceps_ainda_necessarios = {}
    for cep, indices in ceps_novos.items():
        for idx in indices:
            emp = empresas[idx]
            endereco = str(emp.get("endereco", "")).strip()
            municipio = str(emp.get("municipio", "")).strip()
            chave_addr = f"addr:{endereco}|{municipio}|{uf}" if endereco and municipio else None

            # Se endereço não foi resolvido, tentar pelo CEP
            if chave_addr is None or chave_addr not in cache or cache[chave_addr] is None:
                ceps_ainda_necessarios.setdefault(cep, []).append(idx)
                break  # Só precisa marcar o CEP uma vez

    if ceps_ainda_necessarios:
        total_cep = len(ceps_ainda_necessarios)
        print(f"\n  [AwesomeAPI] Geocodificando {total_cep:,} CEPs (4 req/s)...")
        print(f"  Estimativa: ~{total_cep * 0.25 / 60:.0f} min")

        sucesso_cep = 0
        falha_cep = 0

        for i, cep in enumerate(ceps_ainda_necessarios):
            resultado = _geocodificar_cep_awesomeapi(cep)
            if resultado:
                cache[cep] = resultado
                sucesso_cep += 1
            else:
                cache[cep] = None
                falha_cep += 1

            time.sleep(0.25)

            if (i + 1) % 500 == 0:
                _salvar_cache(cache)
                print(f"    AwesomeAPI: {i + 1}/{total_cep} (OK: {sucesso_cep}, falha: {falha_cep})")

        _salvar_cache(cache)
        print(f"  AwesomeAPI concluído: {sucesso_cep} OK, {falha_cep} falhas")

    # === Fase 3: Aplicar coordenadas em todas as empresas ===
    aplicados = 0
    fallback_cep = 0
    fallback_ibge = 0

    for i, emp in enumerate(empresas):
        lat = emp.get("lat")
        if lat is not None and lat != "" and lat != "None":
            aplicados += 1
            continue

        endereco = str(emp.get("endereco", "")).strip()
        municipio = str(emp.get("municipio", "")).strip()
        cep = str(emp.get("cep", "")).strip()

        # Tentar: endereço (Nominatim cache)
        if endereco and municipio:
            chave_addr = f"addr:{endereco}|{municipio}|{uf}"
            if chave_addr in cache and cache[chave_addr] is not None:
                emp["lat"] = cache[chave_addr]["lat"]
                emp["lon"] = cache[chave_addr]["lon"]
                aplicados += 1
                continue

        # Fallback: CEP (AwesomeAPI cache)
        if cep and cep in cache and cache[cep] is not None:
            emp["lat"] = cache[cep]["lat"]
            emp["lon"] = cache[cep]["lon"]
            aplicados += 1
            fallback_cep += 1
            continue

        # Fallback: centroide município (IBGE)
        if lookup_ibge:
            mun = _normalizar(municipio)
            if mun in lookup_ibge:
                emp["lat"] = lookup_ibge[mun]["lat"]
                emp["lon"] = lookup_ibge[mun]["lon"]
                aplicados += 1
                fallback_ibge += 1
                continue

    # Salvar
    _salvar_json(f"{uf}.json", empresas, diretorio=UF_DIR)

    pct = aplicados / len(empresas) * 100 if empresas else 0
    print(f"\n  Resultado {uf}:")
    print(f"    Com coordenadas: {aplicados:,}/{len(empresas):,} ({pct:.1f}%)")
    if fallback_cep:
        print(f"    Via CEP (fallback): {fallback_cep:,}")
    if fallback_ibge:
        print(f"    Via IBGE município (fallback): {fallback_ibge:,}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Geocodificar municípios e endereços")
    parser.add_argument(
        "--uf", type=str, default=None,
        help="UF para geocodificação individual (ex: SC). Sem este flag, enriquece municípios."
    )
    args = parser.parse_args()

    print(f"=== Geocodificação - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    df_municipios = baixar_municipios_ibge()
    if df_municipios.empty:
        print("  [ERRO] Não foi possível obter dados IBGE")
        return

    lookup = _construir_lookup_ibge(df_municipios)
    if not lookup:
        print("  [ERRO] Lookup vazio")
        return

    if args.uf:
        uf = args.uf.upper()
        print(f"\nModo: geocodificação individual para UF={uf}")
        print("  Estratégia: Nominatim (endereço) -> AwesomeAPI (CEP) -> IBGE (município)")
        geocodificar_uf(uf, lookup_ibge=lookup)
    else:
        print("\nModo: enriquecimento de municípios com coordenadas IBGE")
        enriquecer_municipios(lookup)

    print(f"\n=== Concluído - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")


if __name__ == "__main__":
    main()
