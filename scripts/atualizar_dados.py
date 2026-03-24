"""Script para buscar dados das APIs e salvar como cache local em data/.

Roda localmente (python scripts/atualizar_dados.py) ou via GitHub Actions.
"""

import json
import os
import urllib.parse
from datetime import datetime, timedelta

import pandas as pd
import requests

# === Configuração ===
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
TRANSPOCRED_CNPJ_8 = "08075352"
IFDATA_BASE = "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata"
BCBASE_URL = "https://olinda.bcb.gov.br/olinda/servico/BcBase/versao/v2/odata"

SGS = {
    "selic": 4189,
    "cdi": 4391,
    "ipca": 433,
    "igpm": 189,
    "dolar": 1,
    "coop_qtd": 24869,
    "coop_credito_pf": 25518,
    "coop_credito_pj": 25519,
    "coop_depositos_pf": 25517,
    "coop_central": 25509,
    "coop_singular": 25510,
}

IFDATA_RELATORIOS_TRANSPOCRED = {
    "resumo": 1,
    "passivo": 3,
    "dre": 4,
    "capital": 5,
    "credito_pf": 11,
    "credito_pj": 13,
}

# ANTT
ANTT_VEICULOS_CSV = (
    "https://dados.antt.gov.br/dataset/2b564396-5593-4b5c-ba2c-3de3fa0a92c0/"
    "resource/4baf37f1-ac1b-413b-901d-8552a0575605/download/rntrc-veiculos.csv"
)
ANTT_TRANSPORTADORES_CKAN = "https://dados.antt.gov.br/api/3/action/package_show?id=rntrc"

# ANP
ANP_RECENTE_URL = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/qus/ultimas-4-semanas-diesel-gnv.csv"
ANP_MENSAL_BASE = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsan"

# Mapeamento UF nome -> sigla
UF_NOME_PARA_SIGLA = {
    "Acre": "AC", "Alagoas": "AL", "Amapa": "AP", "Amazonas": "AM",
    "Bahia": "BA", "Ceara": "CE", "Distrito Federal": "DF", "Espirito Santo": "ES",
    "Goias": "GO", "Maranhao": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG", "Para": "PA", "Paraiba": "PB", "Parana": "PR",
    "Pernambuco": "PE", "Piaui": "PI", "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS", "Rondonia": "RO",
    "Roraima": "RR", "Santa Catarina": "SC", "Sao Paulo": "SP",
    "Sergipe": "SE", "Tocantins": "TO",
    "Amapá": "AP", "Ceará": "CE", "Espírito Santo": "ES",
    "Goiás": "GO", "Maranhão": "MA", "Pará": "PA", "Paraíba": "PB",
    "Paraná": "PR", "Piauí": "PI", "Rondônia": "RO", "São Paulo": "SP",
}


def _salvar_json(subdir, arquivo, dados):
    """Salva lista de dicts como JSON."""
    caminho = os.path.join(DATA_DIR, subdir, arquivo)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, default=str)
    n = len(dados) if isinstance(dados, (list, dict)) else 0
    print(f"  [OK] {subdir}/{arquivo} - {n} registros")


def _get_ifdata_datas_base():
    """Retorna lista das datas-base disponíveis no IF.data."""
    hoje = datetime.now()
    datas = []
    for ano in range(hoje.year, hoje.year - 4, -1):
        for mes in [12, 9, 6, 3]:
            dt_trimestre = datetime(ano, mes, 1)
            if dt_trimestre < hoje - timedelta(days=60):
                datas.append(f"{ano}{mes:02d}")
    return datas


def _buscar_ifdata(relatorio, data_base, cnpj_8=None, tipo_instituicao=1, timeout=300):
    """Busca dados do IF.data."""
    url = (
        f"{IFDATA_BASE}/IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,"
        f"Relatorio=@Relatorio)"
        f"?@AnoMes={data_base}&@TipoInstituicao={tipo_instituicao}"
        f"&@Relatorio=%27{relatorio}%27"
        f"&$format=json&$top=10000"
    )
    if cnpj_8:
        url += "&$filter=" + urllib.parse.quote(f"CodInst eq '{cnpj_8}'")

    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    dados = resp.json()
    registros = dados.get("value", [])
    if not registros:
        return pd.DataFrame()
    df = pd.DataFrame(registros)
    if "Saldo" in df.columns:
        df["Valor"] = pd.to_numeric(df["Saldo"], errors="coerce")
    if "NomeConta" not in df.columns:
        if "NomeColuna" in df.columns:
            df["NomeConta"] = df["NomeColuna"]
        elif "DescricaoColuna" in df.columns:
            df["NomeConta"] = df["DescricaoColuna"]
        elif "Conta" in df.columns:
            df["NomeConta"] = df["Conta"]
    return df


def _encontrar_data_base_disponivel(cnpj_8=None, max_tentativas=4):
    """Tenta datas-base sucessivas até encontrar uma com dados."""
    datas = _get_ifdata_datas_base()
    for dt in datas[:max_tentativas]:
        try:
            df = _buscar_ifdata(1, dt, cnpj_8=cnpj_8)
            if not df.empty:
                return dt
        except Exception:
            continue
    return datas[0] if datas else "202312"


def _url_diesel_mensal(ano, mes):
    """Monta URL do CSV mensal de diesel conforme padrão do ano."""
    if ano >= 2026:
        return f"{ANP_MENSAL_BASE}/{ano}/{mes:02d}-dados-abertos-precos-diesel-gnv.csv"
    else:
        return f"{ANP_MENSAL_BASE}/{ano}/precos-diesel-gnv-{mes:02d}.csv"


def _ler_csv_anp(url):
    """Lê CSV de diesel da ANP e retorna DataFrame normalizado."""
    df = pd.read_csv(url, sep=";", encoding="latin-1", dtype=str, on_bad_lines="skip")
    df.columns = [c.strip() for c in df.columns]
    col_uf = next((c for c in df.columns if "Estado" in c and "Sigla" in c), None)
    col_produto = next((c for c in df.columns if "Produto" in c), None)
    col_valor = next((c for c in df.columns if "Valor de Venda" in c), None)
    col_data = next((c for c in df.columns if "Data da Coleta" in c), None)
    if not all([col_uf, col_produto, col_valor, col_data]):
        return pd.DataFrame()
    df = df[[col_uf, col_produto, col_valor, col_data]]
    df.columns = ["UF", "Produto", "Valor_Venda", "Data_Coleta"]
    df = df[df["Produto"].str.contains("DIESEL", case=False, na=False)]
    df["Valor_Venda"] = df["Valor_Venda"].str.replace(",", ".").astype(float, errors="ignore")
    df["Valor_Venda"] = pd.to_numeric(df["Valor_Venda"], errors="coerce")
    df["Data_Coleta"] = pd.to_datetime(df["Data_Coleta"], format="%d/%m/%Y", errors="coerce")
    return df.dropna(subset=["Valor_Venda"])


# ============================================================
# 1. Séries SGS
# ============================================================

def buscar_e_salvar_sgs():
    """Busca todas as séries SGS e salva em data/bcb/."""
    print("\n=== Séries SGS ===")
    hoje = datetime.now()
    data_inicio = (hoje - timedelta(days=5 * 365)).strftime("%d/%m/%Y")

    for nome, codigo in SGS.items():
        try:
            url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
            params = {"formato": "json", "dataInicial": data_inicio}
            resp = requests.get(url, params=params, timeout=60)

            # Se 404 com filtro de data (série anual antiga), tentar sem filtro
            if resp.status_code == 404:
                print(f"  [RETRY] sgs_{nome}.json - tentando sem filtro de data...")
                params = {"formato": "json"}
                resp = requests.get(url, params=params, timeout=60)

            resp.raise_for_status()
            dados = resp.json()
            if dados:
                df = pd.DataFrame(dados)
                df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y").dt.strftime("%Y-%m-%d")
                df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
                df = df.dropna(subset=["valor"])
                _salvar_json("bcb", f"sgs_{nome}.json", df.to_dict(orient="records"))
            else:
                print(f"  [VAZIO] sgs_{nome}.json")
        except Exception as e:
            print(f"  [ERRO] sgs_{nome}.json: {e}")


# ============================================================
# 2. IF.data Transpocred (relatórios individuais)
# ============================================================

def buscar_e_salvar_ifdata_transpocred():
    """Busca dados IF.data filtrados para Transpocred e salva."""
    print("\n=== IF.data Transpocred ===")
    data_base = _encontrar_data_base_disponivel(cnpj_8=TRANSPOCRED_CNPJ_8)
    print(f"  Data-base disponível: {data_base}")

    for nome, relatorio in IFDATA_RELATORIOS_TRANSPOCRED.items():
        try:
            df = _buscar_ifdata(relatorio, data_base, cnpj_8=TRANSPOCRED_CNPJ_8)
            if not df.empty:
                _salvar_json("bcb", f"ifdata_transpocred_{nome}.json", df.to_dict(orient="records"))
            else:
                print(f"  [VAZIO] ifdata_transpocred_{nome}.json")
        except Exception as e:
            print(f"  [ERRO] ifdata_transpocred_{nome}.json: {e}")


# ============================================================
# 3. IF.data Evolução (12 trimestres)
# ============================================================

def buscar_e_salvar_ifdata_evolucao():
    """Busca 12 trimestres do relatório 1 para Transpocred."""
    print("\n=== IF.data Evolução Trimestral ===")
    datas = _get_ifdata_datas_base()[:12]
    frames = []

    for dt in datas:
        try:
            df = _buscar_ifdata(1, dt, cnpj_8=TRANSPOCRED_CNPJ_8)
            if not df.empty:
                df["DataBase"] = dt
                frames.append(df)
                print(f"  [OK] Trimestre {dt}")
            else:
                print(f"  [VAZIO] Trimestre {dt}")
        except Exception as e:
            print(f"  [ERRO] Trimestre {dt}: {e}")

    if frames:
        df_all = pd.concat(frames, ignore_index=True)
        _salvar_json("bcb", "ifdata_transpocred_evolucao.json", df_all.to_dict(orient="records"))
    else:
        print("  [VAZIO] Nenhum dado de evolução obtido")


# ============================================================
# 4. IF.data Ranking (todas as cooperativas)
# ============================================================

def _buscar_cadastro_cooperativas(data_base):
    """Busca cadastro IF.data e retorna mapeamento CodInst -> NomeInstituição para cooperativas."""
    url = (
        f"{IFDATA_BASE}/IfDataCadastro(AnoMes=@AnoMes)"
        f"?@AnoMes={data_base}"
        f"&$format=json&$top=10000"
    )
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    registros = resp.json().get("value", [])
    # Filtrar apenas cooperativas de crédito
    mapa = {}
    for r in registros:
        if "Cooperativa" in str(r.get("SegmentoTb", "")):
            mapa[r["CodInst"]] = r["NomeInstituicao"]
    return mapa


def buscar_e_salvar_ifdata_ranking():
    """Busca relatório 1 de TODAS as cooperativas (para ranking)."""
    print("\n=== IF.data Ranking (todas as cooperativas) ===")
    print("  Isso pode levar até 5 minutos...")
    data_base = _encontrar_data_base_disponivel(cnpj_8=TRANSPOCRED_CNPJ_8)
    print(f"  Data-base: {data_base}")

    try:
        # 1. Buscar cadastro para obter nomes e filtrar cooperativas
        print("  Buscando cadastro de instituições...")
        mapa_nomes = _buscar_cadastro_cooperativas(data_base)
        print(f"  Cooperativas no cadastro: {len(mapa_nomes)}")

        # 2. Buscar valores (instituições individuais = tipo 3)
        print("  Buscando dados financeiros (instituições individuais)...")
        url = (
            f"{IFDATA_BASE}/IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,"
            f"Relatorio=@Relatorio)"
            f"?@AnoMes={data_base}&@TipoInstituicao=3"
            f"&@Relatorio=%271%27"
            f"&$format=json&$top=100000"
        )
        resp = requests.get(url, timeout=600)
        resp.raise_for_status()
        registros = resp.json().get("value", [])
        print(f"  Total registros recebidos: {len(registros)}")

        if not registros:
            print("  [VAZIO] ifdata_todas_cooperativas.json")
            return

        # 3. Filtrar apenas cooperativas e adicionar nome
        coop_codigos = set(mapa_nomes.keys())
        registros_coops = []
        for r in registros:
            if r.get("CodInst") in coop_codigos:
                r["NomeInstituicao"] = mapa_nomes[r["CodInst"]]
                registros_coops.append(r)

        print(f"  Registros de cooperativas: {len(registros_coops)}")

        if registros_coops:
            df = pd.DataFrame(registros_coops)
            if "Saldo" in df.columns:
                df["Valor"] = pd.to_numeric(df["Saldo"], errors="coerce")
            if "NomeConta" not in df.columns:
                if "NomeColuna" in df.columns:
                    df["NomeConta"] = df["NomeColuna"]
            _salvar_json("bcb", "ifdata_todas_cooperativas.json", df.to_dict(orient="records"))
        else:
            print("  [VAZIO] ifdata_todas_cooperativas.json (nenhuma cooperativa encontrada)")
    except Exception as e:
        print(f"  [ERRO] ifdata_todas_cooperativas.json: {e}")


# ============================================================
# 5. Sedes de cooperativas (BcBase v2)
# ============================================================

def buscar_e_salvar_sedes():
    """Busca cooperativas ativas via BcBase v2."""
    print("\n=== Cooperativas (BcBase v2) ===")
    data_ref = datetime.now().strftime("01/%m/%Y")
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
        if registros:
            # Adicionar coluna UF (sigla)
            for r in registros:
                nome_uf = r.get("nomeDaUnidadeFederativa", "")
                r["UF"] = UF_NOME_PARA_SIGLA.get(nome_uf, "")
            _salvar_json("bcb", "sedes_cooperativas.json", registros)
        else:
            print("  [VAZIO] sedes_cooperativas.json")
    except Exception as e:
        print(f"  [ERRO] sedes_cooperativas.json: {e}")


# ============================================================
# 6. ANTT - RNTRC
# ============================================================

def _obter_url_transportadores():
    """Obtém URL mais recente do CSV de transportadores via API CKAN."""
    try:
        resp = requests.get(ANTT_TRANSPORTADORES_CKAN, timeout=30)
        resp.raise_for_status()
        dados = resp.json()
        resources = dados.get("result", {}).get("resources", [])
        for r in reversed(resources):
            url = r.get("url", "")
            if "transportadores" in url.lower() and url.endswith(".csv"):
                return url
    except Exception:
        pass
    return None


def buscar_e_salvar_antt():
    """Busca dados ANTT e salva resumos agregados."""
    print("\n=== ANTT RNTRC ===")

    # Veículos
    try:
        print("  Baixando CSV de veículos...")
        df = pd.read_csv(
            ANTT_VEICULOS_CSV, sep=";", encoding="latin-1", dtype=str, on_bad_lines="skip",
        )
        df.columns = [c.strip().lower() for c in df.columns]

        # Identificar colunas dinamicamente        col_uf = next((c for c in df.columns if "uf" in c), None)
        col_tipo = next((c for c in df.columns if "tipo" in c and "veic" in c), None)
        col_ano = next((c for c in df.columns if "ano" in c and "fabric" in c), None)

        resumo = {"total": len(df)}

        if col_uf:
            por_uf = df.groupby(col_uf).size().reset_index(name="Total")
            por_uf.columns = ["UF_Veiculo", "Total"]
            resumo["por_uf"] = por_uf.to_dict(orient="records")

        if col_tipo:
            por_tipo = df.groupby(col_tipo).size().reset_index(name="Total")
            por_tipo.columns = ["Tipo_Veiculo", "Total"]
            resumo["por_tipo"] = por_tipo.to_dict(orient="records")

        if col_ano:
            df_idade = df.copy()
            df_idade[col_ano] = pd.to_numeric(df_idade[col_ano], errors="coerce")
            df_idade = df_idade.dropna(subset=[col_ano])
            df_idade["Idade"] = datetime.now().year - df_idade[col_ano]
            bins = [0, 5, 10, 15, 20, 100]
            labels = ["0-5 anos", "6-10 anos", "11-15 anos", "16-20 anos", "20+ anos"]
            df_idade["Faixa_Idade"] = pd.cut(df_idade["Idade"], bins=bins, labels=labels, right=True)
            por_idade = df_idade.groupby("Faixa_Idade", observed=True).size().reset_index(name="Quantidade")
            resumo["por_idade"] = por_idade.to_dict(orient="records")

        _salvar_json("antt", "rntrc_veiculos_resumo.json", resumo)

    except Exception as e:
        print(f"  [ERRO] rntrc_veiculos_resumo.json: {e}")

    # Transportadores
    try:
        url_csv = _obter_url_transportadores()
        if not url_csv:
            print("  [ERRO] Não foi possível obter URL de transportadores via CKAN")
            return

        print(f"  Baixando CSV de transportadores (chunks)...")
        chunks = pd.read_csv(
            url_csv, sep=";", encoding="latin-1", dtype=str, chunksize=50000, on_bad_lines="skip",
        )
        frames = []
        for chunk in chunks:
            chunk.columns = [c.strip().lower() for c in chunk.columns]
            col_uf = next((c for c in chunk.columns if c == "uf"), None)
            col_cat = next((c for c in chunk.columns if "categoria" in c), None)
            col_sit = next((c for c in chunk.columns if "situacao" in c), None)
            if col_uf and col_cat and col_sit:
                chunk = chunk.rename(columns={col_uf: "UF", col_cat: "Categoria", col_sit: "Situacao"})
                resumo = chunk.groupby(["UF", "Categoria", "Situacao"]).size().reset_index(name="Quantidade")
                frames.append(resumo)

        if frames:
            df_transp = pd.concat(frames, ignore_index=True)
            df_transp = df_transp.groupby(["UF", "Categoria", "Situacao"])["Quantidade"].sum().reset_index()
            _salvar_json("antt", "rntrc_transportadores_resumo.json", df_transp.to_dict(orient="records"))
        else:
            print("  [VAZIO] rntrc_transportadores_resumo.json")

    except Exception as e:
        print(f"  [ERRO] rntrc_transportadores_resumo.json: {e}")


# ============================================================
# 7. ANP - Diesel
# ============================================================

def buscar_e_salvar_anp():
    """Busca preços de diesel da ANP e salva."""
    print("\n=== ANP Diesel ===")
    hoje = datetime.now()

    # Diesel recente: últimas 4 semanas (URL fixa)
    try:
        df_recente = _ler_csv_anp(ANP_RECENTE_URL)
        if not df_recente.empty:
            df_recente["Data_Coleta"] = df_recente["Data_Coleta"].dt.strftime("%Y-%m-%d")
            _salvar_json("anp", "diesel_recente.json", df_recente.to_dict(orient="records"))
        else:
            print("  [VAZIO] diesel_recente.json (últimas 4 semanas)")
    except Exception as e:
        print(f"  [ERRO] diesel_recente.json: {e}")
        # Fallback: CSVs mensais
        frames_recente = []
        for i in range(3):
            ano, mes = hoje.year, hoje.month - i
            if mes <= 0:
                mes += 12
                ano -= 1
            try:
                url = _url_diesel_mensal(ano, mes)
                df = _ler_csv_anp(url)
                if not df.empty:
                    df["Data_Coleta"] = df["Data_Coleta"].dt.strftime("%Y-%m-%d")
                    frames_recente.append(df)
                    print(f"  [OK] ANP mensal {ano}-{mes:02d}")
            except Exception:
                pass
        if frames_recente:
            df_r = pd.concat(frames_recente, ignore_index=True)
            _salvar_json("anp", "diesel_recente.json", df_r.to_dict(orient="records"))

    # Diesel histórico (2 anos, semestral)
    ano_inicio = hoje.year - 2
    frames_hist = []
    for ano in range(ano_inicio, hoje.year + 1):
        for mes in [1, 6]:
            if ano == hoje.year and mes > hoje.month:
                continue
            try:
                url = _url_diesel_mensal(ano, mes)
                df = _ler_csv_anp(url)
                if not df.empty:
                    resumo = df.groupby("UF").agg(
                        Preco_Medio=("Valor_Venda", "mean"),
                        Data=("Data_Coleta", "max"),
                    ).reset_index()
                    resumo["Ano"] = ano
                    resumo["Mes"] = mes
                    resumo["Data"] = resumo["Data"].dt.strftime("%Y-%m-%d")
                    frames_hist.append(resumo)
                    print(f"  [OK] ANP histórico {ano}-{mes:02d}")
            except Exception as e:
                print(f"  [SKIP] ANP histórico {ano}-{mes:02d}: {e}")

    if frames_hist:
        df_hist = pd.concat(frames_hist, ignore_index=True)
        _salvar_json("anp", "diesel_historico.json", df_hist.to_dict(orient="records"))
    else:
        print("  [VAZIO] diesel_historico.json")


# ============================================================
# Main
# ============================================================

def main():
    print(f"=== Atualização de dados - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    print(f"Diretório de dados: {os.path.abspath(DATA_DIR)}")

    buscar_e_salvar_sgs()
    buscar_e_salvar_ifdata_transpocred()
    buscar_e_salvar_ifdata_evolucao()
    buscar_e_salvar_ifdata_ranking()
    buscar_e_salvar_sedes()
    buscar_e_salvar_antt()
    buscar_e_salvar_anp()

    print(f"\n=== Concluído - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")


if __name__ == "__main__":
    main()
