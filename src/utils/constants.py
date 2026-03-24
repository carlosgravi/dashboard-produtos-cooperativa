"""Constantes do projeto: CNPJ, códigos SGS, URLs, paleta de cores."""

# === Transpocred ===
TRANSPOCRED_CNPJ_8 = "08075352"
TRANSPOCRED_NOME = "TRANSPOCRED"

# === BCB SGS - Códigos de séries temporais ===
SGS = {
    # Indicadores econômicos
    "SELIC": 4189,
    "CDI": 4391,
    "IPCA": 433,
    "IGPM": 189,
    "DOLAR_PTAX": 1,
    # Cooperativismo (séries anuais, dados até 2018)
    "COOP_QTD": 24869,           # Quantidade de cooperativas
    "COOP_CREDITO_PF": 25518,    # Saldo crédito PF cooperativas
    "COOP_CREDITO_PJ": 25519,    # Saldo crédito PJ cooperativas
    "COOP_DEPOSITOS_PF": 25517,  # Depósitos à vista PF cooperativas
    "COOP_CENTRAL": 25509,       # Cooperativas centrais
    "COOP_SINGULAR": 25510,      # Cooperativas singulares
}

# === BCB IF.data ===
IFDATA_BASE_URL = "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata"
IFDATA_RELATORIOS = {
    "RESUMO": 1,           # Resumo (Ativo Total, PL, Carteira Crédito, etc.)
    "ATIVO": 2,             # Ativo
    "PASSIVO": 3,           # Passivo (depósitos, captação)
    "DRE": 4,               # Demonstração de Resultado
    "INFO_CAPITAL": 5,      # Informações de Capital (Basileia, etc.)
    "SEGMENTACAO": 6,       # Segmentação
    "CREDITO_PF": 11,       # Carteira de crédito ativa PF - modalidade e prazo
    "CREDITO_PJ": 13,       # Carteira de crédito ativa PJ - modalidade e prazo
}

# Tipos de instituição IF.data (parâmetro TipoInstituicao)
IFDATA_TIPO = {
    "CONGL_PRUDENCIAL": 1,  # Conglomerados Prudenciais e Inst. Independentes
    "CONGL_FINANCEIRO": 2,  # Conglomerados Financeiros e Inst. Independentes
    "INDIVIDUAL": 3,        # Instituições Individuais
    "CAMBIO": 4,            # Instituições com Operações de Câmbio
}

# === BCB BcBase (cadastro cooperativas) ===
BCBASE_URL = "https://olinda.bcb.gov.br/olinda/servico/BcBase/versao/v2/odata"

# === BCB Instituições em funcionamento ===
INSTITUICOES_URL = "https://olinda.bcb.gov.br/olinda/servico/Instituicoes_em_funcionamento/versao/v2/odata"

# === ANTT RNTRC ===
ANTT_BASE_URL = "https://dados.antt.gov.br/dataset/rntrc"
ANTT_VEICULOS_CSV = "https://dados.antt.gov.br/dataset/2b564396-5593-4b5c-ba2c-3de3fa0a92c0/resource/4baf37f1-ac1b-413b-901d-8552a0575605/download/rntrc-veiculos.csv"
# Transportadores: URL dinâmica via CKAN API (muda mensalmente)
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

# === Layout padrão Plotly ===
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

# === CNAEs de transporte/logística/correios ===
CNAES_TRANSPORTE = {
    # Transporte rodoviário de cargas
    "4930201": "Transporte rodoviário de carga municipal",
    "4930202": "Transporte rodoviário de carga intermunicipal/interestadual",
    "4930203": "Transporte rodoviário de produtos perigosos",
    "4930204": "Transporte rodoviário de mudanças",
    # Transporte rodoviário de passageiros
    "4921301": "Transporte coletivo municipal",
    "4921302": "Transporte coletivo metropolitano",
    "4922101": "Transporte coletivo intermunicipal",
    "4922102": "Transporte coletivo interestadual",
    "4929901": "Fretamento municipal",
    "4929902": "Fretamento intermunicipal/interestadual",
    "4929999": "Outros transportes rodoviários de passageiros",
    # Logística e operadores
    "5250801": "Comissaria de despachos",
    "5250803": "Agenciamento de cargas",
    "5250804": "Organização logística do transporte de carga",
    "5250805": "Operador de transporte multimodal",
    # Armazéns
    "5211701": "Armazéns gerais",
    "5211799": "Depósitos de mercadorias para terceiros",
    "5212500": "Carga e descarga",
    # Correios e entregas
    "5310501": "Correio Nacional (ECT)",
    "5310502": "Franqueadas do Correio Nacional",
    "5320201": "Serviços de malote",
    "5320202": "Serviços de entrega rápida (courier)",
}

# Categorias agrupadas por CNAE
CATEGORIAS_EMPRESAS = {
    "Transporte de Cargas": ["4930201", "4930202", "4930203", "4930204"],
    "Transporte de Passageiros": ["4921301", "4921302", "4922101", "4922102", "4929901", "4929902", "4929999"],
    "Logística": ["5250801", "5250803", "5250804", "5250805"],
    "Armazéns": ["5211701", "5211799", "5212500"],
    "Correios e Entregas": ["5310501", "5310502", "5320201", "5320202"],
}

# === Cores por categoria para mapa ===
CORES_CATEGORIAS_MAPA = {
    "Transporte de Cargas": "blue",
    "Transporte de Passageiros": "green",
    "Logística": "orange",
    "Armazéns": "purple",
    "Correios e Entregas": "red",
}

# === Nominatim (OpenStreetMap) - geocodificação por endereço completo ===
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"

# === AwesomeAPI CEP ===
AWESOMEAPI_CEP_URL = "https://cep.awesomeapi.com.br/json/{cep}"

# === IBGE Municípios (coordenadas) ===
IBGE_MUNICIPIOS_URL = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"
