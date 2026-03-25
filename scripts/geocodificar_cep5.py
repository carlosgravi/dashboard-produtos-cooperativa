"""Geocodifica prefixos CEP-5 via AwesomeAPI para posicionamento no mapa.

Cada CEP-5 (5 primeiros digitos) mapeia para um bairro/distrito.
Resultado: data/empresas/cep5_coordenadas.json com {cep5: [lat, lon]}

Uso:
    python scripts/geocodificar_cep5.py                # todas as UFs
    python scripts/geocodificar_cep5.py --uf SC        # apenas SC
    python scripts/geocodificar_cep5.py --uf SC,PR,RS  # multiplas UFs
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
CACHE_PATH = os.path.join(DATA_DIR, "cep5_coordenadas.json")

AWESOME_API_URL = "https://cep.awesomeapi.com.br/json/{cep}"
RATE_LIMIT = 0.25  # 4 req/s


def carregar_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def salvar_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def extrair_cep5_uf(uf):
    """Extrai CEP-5 unicos de uma UF."""
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

    cep5s = set()
    for d in data:
        cep = str(d.get("cep", "")).strip()
        if len(cep) >= 5 and cep[:5] != "00000":
            cep5s.add(cep[:5])
    return cep5s


def geocodificar_cep5(cep5, session):
    """Geocodifica um CEP-5 completando com 000."""
    cep_completo = cep5 + "000"
    try:
        resp = session.get(AWESOME_API_URL.format(cep=cep_completo), timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            lat = data.get("lat")
            lng = data.get("lng")
            if lat and lng:
                return [round(float(lat), 5), round(float(lng), 5)]
    except Exception:
        pass

    # Fallback: tentar com 001
    cep_completo = cep5 + "001"
    try:
        resp = session.get(AWESOME_API_URL.format(cep=cep_completo), timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            lat = data.get("lat")
            lng = data.get("lng")
            if lat and lng:
                return [round(float(lat), 5), round(float(lng), 5)]
    except Exception:
        pass

    return None


def main():
    parser = argparse.ArgumentParser(description="Geocodificar CEP-5 via AwesomeAPI")
    parser.add_argument("--uf", type=str, default=None, help="UF(s) separadas por virgula (ex: SC,PR,RS)")
    args = parser.parse_args()

    # Listar UFs disponiveis
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

    # Extrair CEP-5 unicos
    todos_cep5 = set()
    for uf in ufs:
        cep5s = extrair_cep5_uf(uf)
        print(f"  {uf}: {len(cep5s)} CEP-5 unicos")
        todos_cep5.update(cep5s)

    print(f"\nTotal CEP-5 unicos: {len(todos_cep5)}")

    # Carregar cache existente
    cache = carregar_cache()
    ja_tem = sum(1 for c in todos_cep5 if c in cache)
    faltam = todos_cep5 - set(cache.keys())
    print(f"Cache existente: {len(cache)} entradas ({ja_tem} ja cobertos)")
    print(f"Faltam geocodificar: {len(faltam)}")

    if not faltam:
        print("Tudo ja geocodificado!")
        return

    tempo_est = len(faltam) * RATE_LIMIT / 60
    print(f"Tempo estimado: {tempo_est:.1f} min\n")

    session = requests.Session()
    ok = 0
    falhas = 0
    inicio = time.time()

    for i, cep5 in enumerate(sorted(faltam), 1):
        coord = geocodificar_cep5(cep5, session)
        if coord:
            cache[cep5] = coord
            ok += 1
        else:
            falhas += 1

        if i % 100 == 0:
            elapsed = time.time() - inicio
            rate = i / elapsed if elapsed > 0 else 0
            restante = (len(faltam) - i) / rate / 60 if rate > 0 else 0
            print(f"  {i}/{len(faltam)} ({ok} ok, {falhas} falhas) - {rate:.1f} req/s - ~{restante:.0f} min restantes")
            salvar_cache(cache)

        time.sleep(RATE_LIMIT)

    # Salvar final
    salvar_cache(cache)
    elapsed = time.time() - inicio
    print(f"\nConcluido em {elapsed/60:.1f} min")
    print(f"  Geocodificados: {ok}")
    print(f"  Falhas: {falhas}")
    print(f"  Total no cache: {len(cache)}")


if __name__ == "__main__":
    main()
