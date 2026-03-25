"""Busca coordenadas de CEPs via CNEFE (Censo 2022) no BigQuery.

Extrai a media das coordenadas por CEP a partir da tabela
basedosdados.br_ibge_censo_2022.cadastro_enderecos.

Resultado: data/empresas/cnefe_cep_coordenadas.json.gz

Uso:
    python scripts/buscar_cnefe_coordenadas.py PROJECT_ID
    python scripts/buscar_cnefe_coordenadas.py PROJECT_ID --uf SC,PR,RS,SP
"""

import argparse
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "empresas")
OUTPUT_PATH = os.path.join(DATA_DIR, "cnefe_cep_coordenadas.json.gz")


def main():
    parser = argparse.ArgumentParser(description="Buscar coordenadas CNEFE no BigQuery")
    parser.add_argument("project_id", help="ID do projeto Google Cloud")
    parser.add_argument("--uf", type=str, default=None,
                        help="UF(s) separadas por virgula (default: todas)")
    args = parser.parse_args()

    import pandas_gbq

    if args.uf:
        ufs = [u.strip().upper() for u in args.uf.split(",")]
        filtro_uf = "AND sigla_uf IN ({})".format(
            ", ".join(f"'{u}'" for u in ufs)
        )
        print(f"Buscando CNEFE para: {', '.join(ufs)}")
    else:
        filtro_uf = ""
        print("Buscando CNEFE para todas as UFs")

    query = f"""
    SELECT
      cep,
      ROUND(AVG(SAFE_CAST(latitude AS FLOAT64)), 6) AS lat,
      ROUND(AVG(SAFE_CAST(longitude AS FLOAT64)), 6) AS lon
    FROM `basedosdados.br_ibge_censo_2022.cadastro_enderecos`
    WHERE latitude IS NOT NULL
      AND latitude != ''
      AND cep IS NOT NULL
      AND cep != ''
      {filtro_uf}
    GROUP BY cep
    HAVING lat IS NOT NULL AND lon IS NOT NULL
    """

    print("Executando query no BigQuery...")
    df = pandas_gbq.read_gbq(query, project_id=args.project_id)
    print(f"CEPs com coordenadas: {len(df):,}")

    # Merge com cache existente (se houver)
    cache = {}
    if os.path.exists(OUTPUT_PATH):
        with gzip.open(OUTPUT_PATH, "rt", encoding="utf-8") as f:
            cache = json.load(f)
        print(f"Cache existente: {len(cache):,} CEPs")

    novos = 0
    for _, row in df.iterrows():
        cep = str(row["cep"]).strip()
        if cep and cep not in cache:
            cache[cep] = [row["lat"], row["lon"]]
            novos += 1

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with gzip.open(OUTPUT_PATH, "wt", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)

    size_mb = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
    print(f"\nSalvo em {OUTPUT_PATH}")
    print(f"  Total CEPs: {len(cache):,}")
    print(f"  Novos nesta execucao: {novos:,}")
    print(f"  Tamanho: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
