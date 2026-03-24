"""Constantes do projeto: CNPJ, codigos SGS, URLs, paleta de cores."""

# === Transpocred ===
TRANSPOCRED_CNPJ_8 = "08075352"
TRANSPOCRED_NOME = "TRANSPOCRED"

# === BCB SGS - Codigos de series temporais ===
SGS = {
    # Indicadores economicos
    "SELIC": 4189,
    "CDI": 4391,
    "IPCA": 433,
    "IGPM": 189,
    "DOLAR_PTAX": 1,
    # Cooperativismo (series anuais, dados ate 2018)
    "COOP_QTD": 24869,           # Quantidade de cooperativas
    "COOP_CREDITO_PF": 25518,    # Saldo credito PF cooperativas
    "COOP_CREDITO_PJ": 25519,    # Saldo credito PJ cooperativas
    "COOP_DEPOSITOS_PF": 25517,  # Depositos a vista PF cooperativas
    "COOP_CENTRAL": 25509,       # Cooperativas centrais
    "COOP_SINGULAR": 25510,      # Cooperativas singulares
}

# === BCB IF.data ===
IFDATA_BASE_URL = "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata"
IFDATA_RELATORIOS = {
    "RESUMO": 1,           # Resumo (Ativo Total, PL, Carteira Credito, etc.)
    "ATIVO": 2,             # Ativo
    "PASSIVO": 3,           # Passivo (depositos, captacao)
    "DRE": 4,               # Demonstracao de Resultado
    "INFO_CAPITAL": 5,      # Informacoes de Capital (Basileia, etc.)
    "SEGMENTACAO": 6,       # Segmentacao
    "CREDITO_PF": 11,       # Carteira de credito ativa PF - modalidade e prazo
    "CREDITO_PJ": 13,       # Carteira de credito ativa PJ - modalidade e prazo
}

# Tipos de instituicao IF.data (parametro TipoInstituicao)
IFDATA_TIPO = {
    "CONGL_PRUDENCIAL": 1,  # Conglomerados Prudenciais e Inst. Independentes
    "CONGL_FINANCEIRO": 2,  # Conglomerados Financeiros e Inst. Independentes
    "INDIVIDUAL": 3,        # Instituicoes Individuais
    "CAMBIO": 4,            # Instituicoes com Operacoes de Cambio
}

# === BCB BcBase (cadastro cooperativas) ===
BCBASE_URL = "https://olinda.bcb.gov.br/olinda/servico/BcBase/versao/v2/odata"

# === BCB Instituicoes em funcionamento ===
INSTITUICOES_URL = "https://olinda.bcb.gov.br/olinda/servico/Instituicoes_em_funcionamento/versao/v2/odata"

# === ANTT RNTRC ===
ANTT_BASE_URL = "https://dados.antt.gov.br/dataset/rntrc"
ANTT_VEICULOS_CSV = "https://dados.antt.gov.br/dataset/2b564396-5593-4b5c-ba2c-3de3fa0a92c0/resource/4baf37f1-ac1b-413b-901d-8552a0575605/download/rntrc-veiculos.csv"
# Transportadores: URL dinamica via CKAN API (muda mensalmente)
ANTT_TRANSPORTADORES_CKAN = "https://dados.antt.gov.br/api/3/action/package_show?id=rntrc"

# === ANP Diesel ===
ANP_DIESEL_RECENTE_URL = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/qus/ultimas-4-semanas-diesel-gnv.csv"
ANP_DIESEL_MENSAL_URL = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsan"

# === GeoJSON Brasil ===
GEOJSON_BRASIL_URL = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"

# === Paleta de cores ===
CORES = {
    "verde_ailos": "#00A651",
    "verde_escuro": "#007A3D",
    "verde_claro": "#66CC99",
    "azul": "#1F77B4",
    "azul_escuro": "#0D4F8B",
    "laranja": "#FF7F0E",
    "vermelho": "#D62728",
    "cinza": "#7F7F7F",
    "cinza_claro": "#D3D3D3",
    "amarelo": "#FFD700",
}

PALETA_SEQUENCIAL = [
    "#00A651", "#007A3D", "#66CC99", "#1F77B4",
    "#FF7F0E", "#D62728", "#9467BD", "#8C564B",
    "#E377C2", "#7F7F7F",
]

# === Layout padrao Plotly ===
LAYOUT_PADRAO = dict(
    font=dict(family="Arial, sans-serif", size=12),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(l=40, r=20, t=50, b=40),
    hovermode="x unified",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
)

# === UFs Brasil ===
UFS_BRASIL = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

# === Mapeamento UF Nome -> Sigla ===
UF_NOME_PARA_SIGLA = {
    "Acre": "AC", "Alagoas": "AL", "Amapa": "AP", "Amazonas": "AM",
    "Bahia": "BA", "Ceara": "CE", "Distrito Federal": "DF", "Espirito Santo": "ES",
    "Goias": "GO", "Maranhao": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG", "Para": "PA", "Paraiba": "PB", "Parana": "PR",
    "Pernambuco": "PE", "Piaui": "PI", "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS", "Rondonia": "RO",
    "Roraima": "RR", "Santa Catarina": "SC", "Sao Paulo": "SP",
    "Sergipe": "SE", "Tocantins": "TO",
    # Variantes com acentos
    "Amapá": "AP", "Ceará": "CE", "Espírito Santo": "ES",
    "Goiás": "GO", "Maranhão": "MA", "Pará": "PA", "Paraíba": "PB",
    "Paraná": "PR", "Piauí": "PI", "Rondônia": "RO",
    "São Paulo": "SP", "Tocantins": "TO",
}

TODAS_UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]
