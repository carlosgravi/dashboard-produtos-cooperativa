"""Geocodifica CEPs completos (8 digitos) via AwesomeAPI.

Cada CEP urbano mapeia para um logradouro (rua) especifico.
Resultado: data/empresas/cep_coordenadas.json com {cep8: [lat, lon]}

Uso:
    python scripts/geocodificar_ceps_api.py                # todas as UFs
    python scripts/geocodificar_ceps_api.py --uf SC        # apenas SC
    python scripts/geocodificar_ceps_api.py --uf SC,PR,RS  # multiplas UFs
"""

import argparse
import gzip
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "empresas")
UF_DIR = os.path.join(DATA_DIR, "uf")
CACHE_PATH = os.path.join(DATA_DIR, "cep_coordenadas.json")

AWESOME_API_URL = "https://cep.awesomeapi.com.br/json/{cep}"
RATE_LIMIT = 0.26  # ~3.8 req/s (margem de seguranca)


def carregar_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def salvar_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def extrair_ceps_uf(uf):
    """Extrai CEPs completos unicos de uma UF."""
    caminho = os.path.join(UF_DIR, f"{uf}.json.gz")
    if not os.path.exists(caminho):
        caminho = os.path.join(UF_DIR, f"{uf}.json")
    if not os.path.exists(caminho):
        return set()

    if caminho.endswith(".gz"):
        with gzip.open(caminho, "rt", encoding="utf-8") as f:
            data = json.load(f)
    else:
        with open(caminho, "r", encoding="utf-8") as f:
            data = json.load(f)

    ceps = set()
    for d in data:
        cep = str(d.get("cep", "")).strip().replace("-", "")
        if len(cep) == 8 and cep != "00000000" and cep.isdigit():
            ceps.add(cep)
    return ceps


def geocodificar_cep(cep, session):
    """Geocodifica um CEP completo via AwesomeAPI."""
    try:
        resp = session.get(AWESOME_API_URL.format(cep=cep), timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            lat = data.get("lat")
            lng = data.get("lng")
            if lat and lng:
                lat_f, lng_f = float(lat), float(lng)
                if lat_f != 0 and lng_f != 0:
                    return [round(lat_f, 6), round(lng_f, 6)]
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description="Geocodificar CEPs completos via AwesomeAPI")
    parser.add_argument("--uf", type=str, default=None, help="UF(s) separadas por virgula")
    args = parser.parse_args()

    if args.uf:
        ufs = [u.strip().upper() for u in args.uf.split(",")]
    else:
        ufs = []
        if os.path.isdir(UF_DIR):
            for f in os.listdir(UF_DIR):
                if f.endswith(".json.gz"):
                    ufs.append(f.replace(".json.gz", ""))
                elif f.endswith(".json") and len(f) == 7:
                    ufs.append(f.replace(".json", ""))
        ufs = sorted(set(ufs))

    if not ufs:
        print("Nenhuma UF encontrada.")
        return

    todos_ceps = set()
    for uf in ufs:
        ceps = extrair_ceps_uf(uf)
        print(f"  {uf}: {len(ceps):,} CEPs unicos")
        todos_ceps.update(ceps)

    print(f"\nTotal CEPs unicos: {len(todos_ceps):,}")

    cache = carregar_cache()
    ja_tem = sum(1 for c in todos_ceps if c in cache)
    faltam = sorted(todos_ceps - set(cache.keys()))
    print(f"Cache existente: {len(cache):,} entradas ({ja_tem:,} ja cobertos)")
    print(f"Faltam geocodificar: {len(faltam):,}")

    if not faltam:
        print("Tudo ja geocodificado!")
        return

    tempo_est = len(faltam) * RATE_LIMIT / 60
    print(f"Tempo estimado: {tempo_est:.0f} min\n")

    session = requests.Session()
    ok = 0
    falhas = 0
    inicio = time.time()

    for i, cep in enumerate(faltam, 1):
        coord = geocodificar_cep(cep, session)
        if coord:
            cache[cep] = coord
            ok += 1
        else:
            # Marcar como tentado para nao tentar de novo
            cache[cep] = None
            falhas += 1

        if i % 200 == 0:
            elapsed = time.time() - inicio
            rate = i / elapsed if elapsed > 0 else 0
            restante = (len(faltam) - i) / rate / 60 if rate > 0 else 0
            pct = ok / i * 100
            print(f"  {i:,}/{len(faltam):,} ({ok:,} ok {pct:.0f}%, {falhas:,} falhas) - {rate:.1f} req/s - ~{restante:.0f} min restantes")
            salvar_cache(cache)

        time.sleep(RATE_LIMIT)

    salvar_cache(cache)
    elapsed = time.time() - inicio
    total_ok = sum(1 for v in cache.values() if v is not None)
    print(f"\nConcluido em {elapsed/60:.1f} min")
    print(f"  Novos geocodificados: {ok:,}")
    print(f"  Falhas: {falhas:,}")
    print(f"  Total no cache (com coordenadas): {total_ok:,}")


if __name__ == "__main__":
    main()
