"""Pagina 10 - Diretorio de Empresas de Transporte, Logistica e Correios.

Lista/diretorio com filtros avancados por setor, porte, capital social,
municipio e busca textual, com informacoes de contato (telefone/email).
"""

import pandas as pd
import streamlit as st

from src.api.empresas import (
    listar_ufs_com_dados_individuais,
    carregar_empresas_uf,
    filtrar_empresas_avancado,
)
from src.utils.constants import CATEGORIAS_EMPRESAS
from src.utils.formatting import formatar_numero, formatar_moeda
from src.components.kpi_card import kpi_row

st.header("Diretorio de Empresas")
st.markdown("Consulta detalhada de empresas do setor de transporte, logistica e correios com informacoes de contato.")

# === Verificar dados disponiveis ===
ufs_disponiveis = listar_ufs_com_dados_individuais()

if not ufs_disponiveis:
    st.warning(
        "Nenhum dado individual de empresas disponivel. Execute o script de coleta:\n\n"
        "```bash\n"
        "python scripts/buscar_empresas_transporte.py <PROJECT_ID> --uf SC\n"
        "```"
    )
    st.stop()

# === Sidebar - Filtros ===
with st.sidebar:
    st.subheader("Filtros - Diretorio")

    uf_selecionada = st.selectbox("UF", ufs_disponiveis, index=0)

# Carregar dados da UF
df_empresas = carregar_empresas_uf(uf_selecionada)

if df_empresas.empty:
    st.warning(f"Nenhuma empresa encontrada para {uf_selecionada}.")
    st.stop()

# Garantir que colunas de contato existam (compatibilidade com JSONs antigos)
for col in ("telefone", "email", "nome_fantasia"):
    if col not in df_empresas.columns:
        df_empresas[col] = ""

# Garantir capital_social numerico
if "capital_social" in df_empresas.columns:
    df_empresas["capital_social"] = pd.to_numeric(df_empresas["capital_social"], errors="coerce").fillna(0)

# Restante dos filtros (dependem dos dados carregados)
with st.sidebar:
    categorias = ["Todas"] + sorted(df_empresas["categoria"].dropna().unique().tolist())
    categoria = st.selectbox("Categoria / Setor", categorias)

    portes_disponiveis = sorted(df_empresas["porte_desc"].dropna().unique().tolist()) if "porte_desc" in df_empresas.columns else []
    porte = st.multiselect("Porte", portes_disponiveis) if portes_disponiveis else []

    col_cap1, col_cap2 = st.columns(2)
    with col_cap1:
        capital_min = st.number_input("Capital Social min (R$)", min_value=0, value=0, step=10000)
    with col_cap2:
        capital_max = st.number_input("Capital Social max (R$)", min_value=0, value=0, step=10000,
                                       help="0 = sem limite")

    municipios = ["Todos"] + sorted(df_empresas["municipio"].dropna().unique().tolist())
    municipio = st.selectbox("Municipio", municipios)

    busca = st.text_input("Busca (nome, CNPJ, endereco, email)", placeholder="Digite para buscar...")

# === Aplicar filtros ===
df_filtrado = filtrar_empresas_avancado(
    df_empresas,
    categoria=categoria,
    municipio=municipio,
    porte=porte if porte else None,
    capital_min=capital_min if capital_min > 0 else None,
    capital_max=capital_max if capital_max > 0 else None,
    busca=busca if busca else None,
)

# === KPIs ===
total = len(df_filtrado)
capital_medio = df_filtrado["capital_social"].mean() if total > 0 and "capital_social" in df_filtrado.columns else 0

kpis = [
    {"label": "Empresas encontradas", "valor": formatar_numero(total)},
    {"label": f"Total em {uf_selecionada}", "valor": formatar_numero(len(df_empresas))},
]

if "porte_desc" in df_filtrado.columns and total > 0:
    porte_counts = df_filtrado["porte_desc"].value_counts()
    maior_porte = porte_counts.index[0] if len(porte_counts) > 0 else "—"
    kpis.append({"label": "Porte predominante", "valor": maior_porte})

kpis.append({"label": "Capital social medio", "valor": formatar_moeda(capital_medio)})

kpi_row(kpis)

# === Resumo por porte ===
if "porte_desc" in df_filtrado.columns and total > 0:
    st.subheader("Distribuicao por Porte")
    porte_resumo = df_filtrado["porte_desc"].value_counts().reset_index()
    porte_resumo.columns = ["Porte", "Quantidade"]
    cols_porte = st.columns(len(porte_resumo) if len(porte_resumo) <= 5 else 5)
    for i, row in porte_resumo.iterrows():
        if i < len(cols_porte):
            with cols_porte[i]:
                st.metric(row["Porte"], formatar_numero(row["Quantidade"]))

# === Tabela de empresas ===
st.subheader(f"Empresas ({formatar_numero(total)} resultados)")

if total == 0:
    st.info("Nenhuma empresa encontrada com os filtros selecionados.")
else:
    # Preparar colunas para exibicao
    colunas_exibir = {
        "cnpj": "CNPJ",
        "nome": "Razao Social",
        "nome_fantasia": "Nome Fantasia",
        "categoria": "Categoria",
        "municipio": "Municipio",
        "porte_desc": "Porte",
        "capital_social": "Capital Social (R$)",
        "telefone": "Telefone",
        "email": "Email",
        "endereco": "Endereco",
    }

    colunas_disponiveis = {k: v for k, v in colunas_exibir.items() if k in df_filtrado.columns}
    df_exibir = df_filtrado[list(colunas_disponiveis.keys())].rename(columns=colunas_disponiveis)

    # Configurar formatacao de colunas
    column_config = {}
    if "Capital Social (R$)" in df_exibir.columns:
        column_config["Capital Social (R$)"] = st.column_config.NumberColumn(
            "Capital Social (R$)", format="R$ %.2f"
        )
    if "Email" in df_exibir.columns:
        column_config["Email"] = st.column_config.TextColumn("Email", width="medium")
    if "Telefone" in df_exibir.columns:
        column_config["Telefone"] = st.column_config.TextColumn("Telefone", width="medium")

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config=column_config,
    )

    # === Download CSV ===
    csv = df_exibir.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        label=f"Download CSV ({formatar_numero(total)} empresas)",
        data=csv,
        file_name=f"diretorio_empresas_{uf_selecionada}.csv",
        mime="text/csv",
    )
