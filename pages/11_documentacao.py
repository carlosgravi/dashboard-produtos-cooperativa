"""Página 11 - Documentação Técnica do Dashboard."""

import streamlit as st

st.header("Documentação Técnica")
st.markdown(
    "Descrição das fontes de dados, APIs, métricas e periodicidade de atualização "
    "utilizadas em cada página do dashboard."
)

# === Visão Geral ===
st.subheader("1. Visão Geral")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Banco Central do Brasil — IF.data (Sistema de Informações de Instituições Financeiras) |
| **API** | OLINDA/BCB — Relatórios 1 (Resumo) e 5 (Informações de Capital) |
| **Métricas** | Ativo Total, Patrimônio Líquido, Operações de Crédito, Depósitos Totais, Capital Social, Índice de Basileia |
| **Periodicidade** | Trimestral (último trimestre disponível) |
| **Atualização** | Semanal (GitHub Actions) |
""")

# === Indicadores Financeiros ===
st.subheader("2. Indicadores Financeiros")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Banco Central do Brasil — IF.data |
| **API** | OLINDA/BCB — Relatórios 3 (Passivo), 4 (DRE), 11 (Crédito PF), 13 (Crédito PJ) |
| **Métricas** | Depósitos (vista/prazo/poupança), Receitas/Despesas de Intermediação, Sobras/Perdas, Crédito PF e PJ por modalidade, Inadimplência (vencido >15 dias) |
| **Periodicidade** | Trimestral |
| **Atualização** | Semanal (GitHub Actions) |
""")

# === Panorama Cooperativismo ===
st.subheader("3. Panorama do Cooperativismo")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Banco Central do Brasil — SGS (Sistema Gerenciador de Séries Temporais) |
| **API** | SGS/BCB — Séries 24869 (qtd. cooperativas), 25509 (centrais), 25510 (singulares), 25517 (depósitos PF), 25518 (crédito PF), 25519 (crédito PJ) |
| **Métricas** | Quantidade de cooperativas, crédito PF/PJ, depósitos, centrais vs singulares |
| **Periodicidade** | Anual (séries históricas até 2018-2022) |
| **Atualização** | Semanal (GitHub Actions) |
""")

# === Comparativo de Mercado ===
st.subheader("4. Comparativo de Mercado")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Banco Central do Brasil — IF.data |
| **API** | OLINDA/BCB — Relatório 1, filtro `TipoInstituicao=3` (todas as cooperativas singulares) |
| **Métricas** | Ranking por Ativo Total, posição da Transpocred, média e mediana do setor |
| **Periodicidade** | Trimestral |
| **Atualização** | Semanal (GitHub Actions) |
""")

# === Indicadores Econômicos ===
st.subheader("5. Indicadores Econômicos")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Banco Central do Brasil — SGS |
| **API** | SGS/BCB — Séries 4189 (Selic meta), 4391 (CDI), 433 (IPCA), 189 (IGP-M), 1 (Dólar PTAX venda) |
| **Métricas** | Taxa Selic (% a.a.), CDI (% a.a.), IPCA mensal e acumulado 12m, IGP-M mensal, Dólar PTAX (R$) |
| **Periodicidade** | Diária (Selic, CDI, Dólar) / Mensal (IPCA, IGP-M) |
| **Atualização** | Semanal (GitHub Actions) |
""")

# === Setor de Transportes ===
st.subheader("6. Setor de Transportes")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fontes** | ANTT — RNTRC (Registro Nacional de Transportadores) / ANP — SLP (Sistema de Levantamento de Preços) |
| **APIs** | ANTT dados abertos: CSV direto (veículos) + CKAN API (transportadores). ANP dados abertos: CSV de preços de combustíveis |
| **Métricas** | Frota (total, por tipo, por UF, idade), transportadores (TAC/ETC/CTC), preço médio do Diesel por UF |
| **Periodicidade** | ANTT: mensal / ANP: semanal (últimas 4 semanas) |
| **Atualização** | Semanal (GitHub Actions) |
""")

# === Mapa de Atuação ===
st.subheader("7. Mapa de Atuação")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Banco Central do Brasil — BcBase v2 / Cadastro de Cooperativas |
| **API** | OLINDA/BCB — BcBase v2, endpoint `/Cooperativas` |
| **Métricas** | Distribuição geográfica de cooperativas por UF, classe, tipo e categoria |
| **Periodicidade** | Trimestral |
| **Atualização** | Semanal (GitHub Actions) |
""")

# === Mapa de Empresas ===
st.subheader("8. Mapa de Empresas")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Receita Federal do Brasil — Cadastro CNPJ, via Base dos Dados (BigQuery) |
| **APIs** | Google BigQuery (dados cadastrais filtrados por CNAE), Nominatim / AwesomeAPI CEP / IBGE (geocodificação em 3 níveis de fallback) |
| **Métricas** | Empresas por categoria CNAE (Transporte de Cargas, Passageiros, Logística, Armazéns, Correios), porte, capital social, geolocalização |
| **Periodicidade** | Dados RFB atualizados mensalmente na Base dos Dados |
| **Atualização** | Manual via `scripts/buscar_empresas_transporte.py` |
""")

# === Compliance ===
st.subheader("9. Compliance")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fontes** | CGU — CEIS/CNEP (Portal da Transparência), PNCP (Portal Nacional de Contratações Públicas), Consumidor.gov.br |
| **APIs** | Portal da Transparência/CGU (requer chave gratuita), PNCP API (acesso público), dados.gov.br CKAN API |
| **Métricas** | Sanções (CEIS/CNEP), contratos públicos (valor e quantidade), reclamações de consumidor |
| **Periodicidade** | Cache incremental (re-consulta após 30 dias) |
| **Atualização** | Manual via `scripts/buscar_compliance.py` |
""")

# === Diretório de Empresas ===
st.subheader("10. Diretório de Empresas")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Receita Federal do Brasil — Cadastro CNPJ, via Base dos Dados (BigQuery) |
| **Métricas** | Diretório com razão social, CNPJ, contato (telefone/email), porte, capital social, endereço |
| **Periodicidade** | Dados RFB atualizados mensalmente na Base dos Dados |
| **Atualização** | Manual via `scripts/buscar_empresas_transporte.py` |
""")

# === Arquitetura ===
st.markdown("---")
st.subheader("Arquitetura do Dashboard")
st.markdown("""
```
dashboard-produtos-cooperativa/
|-- app.py                    # Entry point (st.navigation)
|-- pages/                    # Páginas do dashboard (1 a 11)
|-- src/
|   |-- api/                  # Camada de acesso a dados
|   |   |-- bcb.py            # BCB: SGS, IF.data, BcBase
|   |   |-- antt.py           # ANTT: RNTRC (veículos, transportadores)
|   |   |-- anp.py            # ANP: preços de diesel
|   |   |-- empresas.py       # RFB/BigQuery: empresas por CNAE
|   |   |-- compliance.py     # CGU, PNCP, Consumidor.gov.br
|   |-- components/           # Componentes visuais reutilizáveis
|   |   |-- kpi_card.py       # Cards de KPI
|   |   |-- charts.py         # Gráficos Plotly padronizados
|   |   |-- kepler_map.py     # Mapa Kepler.gl (WebGL)
|   |-- utils/
|       |-- constants.py      # CNPJs, códigos SGS, URLs, paleta de cores
|       |-- formatting.py     # Formatação BRL, números, percentuais
|-- data/                     # Cache local (JSONs pré-processados)
|   |-- bcb/                  # Dados do Banco Central
|   |-- antt/                 # Dados da ANTT
|   |-- anp/                  # Dados da ANP
|   |-- empresas/             # Dados de empresas (RFB, compliance)
|-- scripts/
|   |-- atualizar_dados.py    # Atualiza cache de todas as APIs públicas
|   |-- buscar_empresas_transporte.py  # Coleta empresas via BigQuery
|   |-- buscar_compliance.py  # Coleta dados de compliance (CGU, PNCP)
|-- .github/workflows/
    |-- atualizar_dados.yml   # GitHub Actions: atualização semanal (seg 6h UTC)
```
""")

# === Fluxo de Dados ===
st.subheader("Fluxo de Dados")
st.markdown("""
1. **Coleta automática (semanal):** GitHub Actions executa `scripts/atualizar_dados.py` toda segunda-feira às 6h UTC, atualizando os caches JSON em `data/` para BCB, ANTT e ANP.

2. **Coleta manual (sob demanda):**
   - Empresas: `python scripts/buscar_empresas_transporte.py <PROJECT_ID> --uf SC`
   - Compliance: `python scripts/buscar_compliance.py --uf SC --api cgu --cgu-api-key CHAVE`

3. **Dashboard:** Cada página tenta carregar do cache local (`data/*.json`) primeiro. Se o cache não existir, faz fallback para a API online com `@st.cache_data` (TTL de 1h para SGS, 24h para IF.data).

4. **Geocodificação:** Três níveis de fallback para converter endereços em coordenadas:
   - Nominatim (endereço completo, 1 req/s)
   - AwesomeAPI CEP (4 req/s)
   - IBGE centroide municipal
""")

# === Glossário ===
st.subheader("Glossário")
st.markdown("""
| Sigla | Significado |
|-------|-------------|
| **BCB** | Banco Central do Brasil |
| **SGS** | Sistema Gerenciador de Séries Temporais (BCB) |
| **IF.data** | Informações Financeiras de Instituições (BCB) |
| **OLINDA** | API de dados abertos do BCB |
| **BcBase** | Cadastro de instituições financeiras do BCB |
| **ANTT** | Agência Nacional de Transportes Terrestres |
| **RNTRC** | Registro Nacional de Transportadores Rodoviários de Cargas |
| **ANP** | Agência Nacional do Petróleo, Gás Natural e Biocombustíveis |
| **SLP** | Sistema de Levantamento de Preços (ANP) |
| **RFB** | Receita Federal do Brasil |
| **CNAE** | Classificação Nacional de Atividades Econômicas |
| **CGU** | Controladoria-Geral da União |
| **CEIS** | Cadastro de Empresas Inidôneas e Suspensas |
| **CNEP** | Cadastro Nacional de Empresas Punidas |
| **PNCP** | Portal Nacional de Contratações Públicas |
| **TAC** | Transportador Autônomo de Cargas |
| **ETC** | Empresa de Transporte de Cargas |
| **CTC** | Cooperativa de Transporte de Cargas |
| **PTAX** | Taxa de câmbio de referência do BCB |
""")
