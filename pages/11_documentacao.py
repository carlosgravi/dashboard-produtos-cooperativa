"""Pagina 11 - Documentacao Tecnica do Dashboard."""

import streamlit as st

st.header("Documentacao Tecnica")
st.markdown(
    "Descricao das fontes de dados, APIs, metricas e periodicidade de atualizacao "
    "utilizadas em cada pagina do dashboard."
)

# === Visao Geral ===
st.subheader("1. Visao Geral")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Banco Central do Brasil — IF.data (Sistema de Informacoes de Instituicoes Financeiras) |
| **API** | OLINDA/BCB — Relatorios 1 (Resumo) e 5 (Informacoes de Capital) |
| **Metricas** | Ativo Total, Patrimonio Liquido, Operacoes de Credito, Depositos Totais, Capital Social, Indice de Basileia |
| **Periodicidade** | Trimestral (ultimo trimestre disponivel) |
| **Atualizacao** | Semanal (GitHub Actions) |
""")

# === Indicadores Financeiros ===
st.subheader("2. Indicadores Financeiros")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Banco Central do Brasil — IF.data |
| **API** | OLINDA/BCB — Relatorios 3 (Passivo), 4 (DRE), 11 (Credito PF), 13 (Credito PJ) |
| **Metricas** | Depositos (vista/prazo/poupanca), Receitas/Despesas de Intermediacao, Sobras/Perdas, Credito PF e PJ por modalidade, Inadimplencia (vencido >15 dias) |
| **Periodicidade** | Trimestral |
| **Atualizacao** | Semanal (GitHub Actions) |
""")

# === Panorama Cooperativismo ===
st.subheader("3. Panorama do Cooperativismo")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Banco Central do Brasil — SGS (Sistema Gerenciador de Series Temporais) |
| **API** | SGS/BCB — Series 24869 (qtd. cooperativas), 25509 (centrais), 25510 (singulares), 25517 (depositos PF), 25518 (credito PF), 25519 (credito PJ) |
| **Metricas** | Quantidade de cooperativas, credito PF/PJ, depositos, centrais vs singulares |
| **Periodicidade** | Anual (series historicas ate 2018-2022) |
| **Atualizacao** | Semanal (GitHub Actions) |
""")

# === Comparativo de Mercado ===
st.subheader("4. Comparativo de Mercado")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Banco Central do Brasil — IF.data |
| **API** | OLINDA/BCB — Relatorio 1, filtro `TipoInstituicao=3` (todas as cooperativas singulares) |
| **Metricas** | Ranking por Ativo Total, posicao da Transpocred, media e mediana do setor |
| **Periodicidade** | Trimestral |
| **Atualizacao** | Semanal (GitHub Actions) |
""")

# === Indicadores Economicos ===
st.subheader("5. Indicadores Economicos")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Banco Central do Brasil — SGS |
| **API** | SGS/BCB — Series 4189 (Selic meta), 4391 (CDI), 433 (IPCA), 189 (IGP-M), 1 (Dolar PTAX venda) |
| **Metricas** | Taxa Selic (% a.a.), CDI (% a.a.), IPCA mensal e acumulado 12m, IGP-M mensal, Dolar PTAX (R$) |
| **Periodicidade** | Diaria (Selic, CDI, Dolar) / Mensal (IPCA, IGP-M) |
| **Atualizacao** | Semanal (GitHub Actions) |
""")

# === Setor de Transportes ===
st.subheader("6. Setor de Transportes")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fontes** | ANTT — RNTRC (Registro Nacional de Transportadores) / ANP — SLP (Sistema de Levantamento de Precos) |
| **APIs** | ANTT dados abertos: CSV direto (veiculos) + CKAN API (transportadores). ANP dados abertos: CSV de precos de combustiveis |
| **Metricas** | Frota (total, por tipo, por UF, idade), transportadores (TAC/ETC/CTC), preco medio do Diesel por UF |
| **Periodicidade** | ANTT: mensal / ANP: semanal (ultimas 4 semanas) |
| **Atualizacao** | Semanal (GitHub Actions) |
""")

# === Mapa de Atuacao ===
st.subheader("7. Mapa de Atuacao")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Banco Central do Brasil — BcBase v2 / Cadastro de Cooperativas |
| **API** | OLINDA/BCB — BcBase v2, endpoint `/Cooperativas` |
| **Metricas** | Distribuicao geografica de cooperativas por UF, classe, tipo e categoria |
| **Periodicidade** | Trimestral |
| **Atualizacao** | Semanal (GitHub Actions) |
""")

# === Mapa de Empresas ===
st.subheader("8. Mapa de Empresas")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Receita Federal do Brasil — Cadastro CNPJ, via Base dos Dados (BigQuery) |
| **APIs** | Google BigQuery (dados cadastrais filtrados por CNAE), Nominatim / AwesomeAPI CEP / IBGE (geocodificacao em 3 niveis de fallback) |
| **Metricas** | Empresas por categoria CNAE (Transporte de Cargas, Passageiros, Logistica, Armazens, Correios), porte, capital social, geolocalizacao |
| **Periodicidade** | Dados RFB atualizados mensalmente na Base dos Dados |
| **Atualizacao** | Manual via `scripts/buscar_empresas_transporte.py` |
""")

# === Compliance ===
st.subheader("9. Compliance")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fontes** | CGU — CEIS/CNEP (Portal da Transparencia), PNCP (Portal Nacional de Contratacoes Publicas), Consumidor.gov.br |
| **APIs** | Portal da Transparencia/CGU (requer chave gratuita), PNCP API (acesso publico), dados.gov.br CKAN API |
| **Metricas** | Sancoes (CEIS/CNEP), contratos publicos (valor e quantidade), reclamacoes de consumidor |
| **Periodicidade** | Cache incremental (re-consulta apos 30 dias) |
| **Atualizacao** | Manual via `scripts/buscar_compliance.py` |
""")

# === Diretorio de Empresas ===
st.subheader("10. Diretorio de Empresas")
st.markdown("""
| Item | Detalhe |
|------|---------|
| **Fonte** | Receita Federal do Brasil — Cadastro CNPJ, via Base dos Dados (BigQuery) |
| **Metricas** | Diretorio com razao social, CNPJ, contato (telefone/email), porte, capital social, endereco |
| **Periodicidade** | Dados RFB atualizados mensalmente na Base dos Dados |
| **Atualizacao** | Manual via `scripts/buscar_empresas_transporte.py` |
""")

# === Arquitetura ===
st.markdown("---")
st.subheader("Arquitetura do Dashboard")
st.markdown("""
```
dashboard-produtos-cooperativa/
|-- app.py                    # Entry point (st.navigation)
|-- pages/                    # Paginas do dashboard (1 a 11)
|-- src/
|   |-- api/                  # Camada de acesso a dados
|   |   |-- bcb.py            # BCB: SGS, IF.data, BcBase
|   |   |-- antt.py           # ANTT: RNTRC (veiculos, transportadores)
|   |   |-- anp.py            # ANP: precos de diesel
|   |   |-- empresas.py       # RFB/BigQuery: empresas por CNAE
|   |   |-- compliance.py     # CGU, PNCP, Consumidor.gov.br
|   |-- components/           # Componentes visuais reutilizaveis
|   |   |-- kpi_card.py       # Cards de KPI
|   |   |-- charts.py         # Graficos Plotly padronizados
|   |   |-- kepler_map.py     # Mapa Kepler.gl (WebGL)
|   |-- utils/
|       |-- constants.py      # CNPJs, codigos SGS, URLs, paleta de cores
|       |-- formatting.py     # Formatacao BRL, numeros, percentuais
|-- data/                     # Cache local (JSONs pre-processados)
|   |-- bcb/                  # Dados do Banco Central
|   |-- antt/                 # Dados da ANTT
|   |-- anp/                  # Dados da ANP
|   |-- empresas/             # Dados de empresas (RFB, compliance)
|-- scripts/
|   |-- atualizar_dados.py    # Atualiza cache de todas as APIs publicas
|   |-- buscar_empresas_transporte.py  # Coleta empresas via BigQuery
|   |-- buscar_compliance.py  # Coleta dados de compliance (CGU, PNCP)
|-- .github/workflows/
    |-- atualizar_dados.yml   # GitHub Actions: atualizacao semanal (seg 6h UTC)
```
""")

# === Fluxo de Dados ===
st.subheader("Fluxo de Dados")
st.markdown("""
1. **Coleta automatica (semanal):** GitHub Actions executa `scripts/atualizar_dados.py` toda segunda-feira as 6h UTC, atualizando os caches JSON em `data/` para BCB, ANTT e ANP.

2. **Coleta manual (sob demanda):**
   - Empresas: `python scripts/buscar_empresas_transporte.py <PROJECT_ID> --uf SC`
   - Compliance: `python scripts/buscar_compliance.py --uf SC --api cgu --cgu-api-key CHAVE`

3. **Dashboard:** Cada pagina tenta carregar do cache local (`data/*.json`) primeiro. Se o cache nao existir, faz fallback para a API online com `@st.cache_data` (TTL de 1h para SGS, 24h para IF.data).

4. **Geocodificacao:** Tres niveis de fallback para converter enderecos em coordenadas:
   - Nominatim (endereco completo, 1 req/s)
   - AwesomeAPI CEP (4 req/s)
   - IBGE centroide municipal
""")

# === Glossario ===
st.subheader("Glossario")
st.markdown("""
| Sigla | Significado |
|-------|-------------|
| **BCB** | Banco Central do Brasil |
| **SGS** | Sistema Gerenciador de Series Temporais (BCB) |
| **IF.data** | Informacoes Financeiras de Instituicoes (BCB) |
| **OLINDA** | API de dados abertos do BCB |
| **BcBase** | Cadastro de instituicoes financeiras do BCB |
| **ANTT** | Agencia Nacional de Transportes Terrestres |
| **RNTRC** | Registro Nacional de Transportadores Rodoviarios de Cargas |
| **ANP** | Agencia Nacional do Petroleo, Gas Natural e Biocombustiveis |
| **SLP** | Sistema de Levantamento de Precos (ANP) |
| **RFB** | Receita Federal do Brasil |
| **CNAE** | Classificacao Nacional de Atividades Economicas |
| **CGU** | Controladoria-Geral da Uniao |
| **CEIS** | Cadastro de Empresas Inidoneas e Suspensas |
| **CNEP** | Cadastro Nacional de Empresas Punidas |
| **PNCP** | Portal Nacional de Contratacoes Publicas |
| **TAC** | Transportador Autonomo de Cargas |
| **ETC** | Empresa de Transporte de Cargas |
| **CTC** | Cooperativa de Transporte de Cargas |
| **PTAX** | Taxa de cambio de referencia do BCB |
""")
