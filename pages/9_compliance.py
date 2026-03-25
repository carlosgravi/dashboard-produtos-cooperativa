"""Pagina 9 - Compliance Empresarial."""

import json

import pandas as pd
import streamlit as st

from src.api.compliance import (
    carregar_compliance_uf,
    carregar_resumo_compliance,
    consultar_empresa_compliance,
    extrair_contratos_pncp,
    extrair_empresas_sancionadas,
    listar_ufs_com_compliance,
    carregar_consumidor_gov,
)
from src.components.charts import grafico_barras, grafico_pizza
from src.components.kpi_card import kpi_row
from src.utils.formatting import formatar_moeda, formatar_numero


# ============================================================
# Funcoes auxiliares (definidas antes do fluxo principal)
# ============================================================

def _parse_json_field(valor):
    """Converte campo que pode ser string JSON ou lista."""
    if isinstance(valor, list):
        return valor
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _exibir_empresa(resultado):
    """Exibe detalhes de compliance de uma empresa."""
    st.markdown(f"**{resultado.get('nome', 'N/A')}** - CNPJ: {resultado.get('cnpj', '')}")
    st.caption(f"Consultado em: {resultado.get('consultado_em', 'N/A')}")

    ceis = _parse_json_field(resultado.get("ceis", []))
    cnep = _parse_json_field(resultado.get("cnep", []))
    pncp = _parse_json_field(resultado.get("pncp_contratos", []))

    col1, col2, col3 = st.columns(3)
    col1.metric("CEIS (Sancoes)", len(ceis))
    col2.metric("CNEP (Punicoes)", len(cnep))
    col3.metric("Contratos PNCP", len(pncp))

    if ceis:
        st.markdown("##### Sancoes CEIS")
        st.dataframe(pd.DataFrame(ceis), use_container_width=True, hide_index=True)

    if cnep:
        st.markdown("##### Punicoes CNEP")
        st.dataframe(pd.DataFrame(cnep), use_container_width=True, hide_index=True)

    if pncp:
        st.markdown("##### Contratos PNCP")
        df_pncp = pd.DataFrame(pncp)
        if "valor" in df_pncp.columns:
            df_pncp["valor"] = pd.to_numeric(df_pncp["valor"], errors="coerce")
        st.dataframe(
            df_pncp, use_container_width=True, hide_index=True,
            column_config={
                "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            },
        )

    if not ceis and not cnep and not pncp:
        st.success("Nenhuma sancao, punicao ou contrato publico encontrado.")


def _exibir_consumidor():
    """Exibe dados do Consumidor.gov.br."""
    st.subheader("Reclamacoes - Consumidor.gov.br")

    df_consumidor = carregar_consumidor_gov()

    if df_consumidor.empty:
        st.info(
            "Dados do Consumidor.gov.br nao disponiveis.\n\n"
            "Execute:\n"
            "```\n"
            "python scripts/buscar_compliance.py --consumidor\n"
            "```"
        )
        return

    st.success(f"{len(df_consumidor):,} reclamacoes carregadas")

    # Normalizar nomes de colunas
    colunas = [c.lower().strip() for c in df_consumidor.columns]
    df_consumidor.columns = colunas

    # Identificar colunas relevantes
    col_empresa = next((c for c in colunas if "empresa" in c or "fornecedor" in c or "razao" in c), None)
    col_nota = next((c for c in colunas if "nota" in c), None)
    col_resolvida = next((c for c in colunas if "resolv" in c or "soluc" in c), None)
    col_segmento = next((c for c in colunas if "segmento" in c or "area" in c or "assunto" in c), None)

    # Filtrar por segmento de transporte se possivel
    if col_segmento:
        termos_transporte = ["transporte", "logistic", "correio", "entrega", "frete"]
        mask = df_consumidor[col_segmento].str.lower().str.contains(
            "|".join(termos_transporte), na=False
        )
        df_transporte = df_consumidor[mask]
        if not df_transporte.empty:
            st.info(f"{len(df_transporte):,} reclamacoes filtradas para transporte/logistica")
            df_consumidor = df_transporte

    # Ranking de empresas mais reclamadas
    if col_empresa:
        st.markdown("#### Empresas Mais Reclamadas")
        df_ranking = (
            df_consumidor[col_empresa].value_counts()
            .head(20).reset_index()
        )
        df_ranking.columns = ["Empresa", "Reclamacoes"]
        st.dataframe(df_ranking, use_container_width=True, hide_index=True)

    # Indice de solucao
    if col_resolvida:
        st.markdown("#### Indice de Solucao")
        total_recl = len(df_consumidor)
        resolvidas = df_consumidor[col_resolvida].str.lower().str.contains(
            "sim|resolvid|soluc", na=False
        ).sum()
        taxa = (resolvidas / total_recl * 100) if total_recl > 0 else 0
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Reclamacoes", formatar_numero(total_recl))
        col2.metric("Resolvidas", formatar_numero(resolvidas))
        col3.metric("Taxa de Solucao", f"{taxa:.1f}%")

    # Nota media
    if col_nota:
        df_consumidor[col_nota] = pd.to_numeric(df_consumidor[col_nota], errors="coerce")
        nota_media = df_consumidor[col_nota].mean()
        if pd.notna(nota_media):
            st.metric("Nota Media do Consumidor", f"{nota_media:.1f}")

    # Amostra
    st.markdown("#### Amostra dos Dados")
    st.dataframe(df_consumidor.head(100), use_container_width=True, hide_index=True)


# ============================================================
# Fluxo principal
# ============================================================

st.header("Compliance Empresarial - Setor Transporte")

ufs_disponiveis = listar_ufs_com_compliance()

# Se nao ha dados por UF, exibir apenas consulta individual e consumidor
if not ufs_disponiveis:
    st.info(
        "Nenhum dado de compliance disponivel.\n\n"
        "Execute o script de coleta para gerar os dados:\n"
        "```\n"
        "python scripts/buscar_compliance.py --uf SC --api cgu --cgu-api-key SUA_CHAVE\n"
        "python scripts/buscar_compliance.py --uf SC --api pncp\n"
        "```"
    )

    tab_consulta, tab_consumidor = st.tabs(["Consulta Individual", "Consumidor.gov.br"])

    with tab_consulta:
        st.subheader("Consultar Empresa por CNPJ")
        cnpj_busca = st.text_input("CNPJ", placeholder="00.000.000/0000-00", key="cnpj_sem_dados")
        if cnpj_busca:
            resultado = consultar_empresa_compliance(cnpj_busca)
            if resultado:
                _exibir_empresa(resultado)
            else:
                st.warning("Empresa nao encontrada no cache local.")

    with tab_consumidor:
        _exibir_consumidor()

    st.caption("Fontes: CGU/CEIS, CGU/CNEP, PNCP, Consumidor.gov.br")
    st.stop()

# === Sidebar ===
uf_selecionada = st.sidebar.selectbox("UF", ufs_disponiveis, index=0)

# === Carregar dados ===
df_compliance = carregar_compliance_uf(uf_selecionada)
resumo = carregar_resumo_compliance()

# === KPIs ===
resumo_uf = resumo.get(uf_selecionada, {})
total_consultados = resumo_uf.get("total_consultados", len(df_compliance))
ceis_total = resumo_uf.get("ceis_encontrados", 0)
cnep_total = resumo_uf.get("cnep_encontrados", 0)
pncp_total = resumo_uf.get("pncp_com_contratos", 0)

# Se resumo nao esta disponivel, calcular dos dados
if not resumo_uf and not df_compliance.empty:
    for _, row in df_compliance.iterrows():
        ceis = _parse_json_field(row.get("ceis", []))
        cnep = _parse_json_field(row.get("cnep", []))
        pncp = _parse_json_field(row.get("pncp_contratos", []))
        if ceis:
            ceis_total += 1
        if cnep:
            cnep_total += 1
        if pncp:
            pncp_total += 1

kpi_row([
    {
        "label": "Empresas Consultadas",
        "valor": formatar_numero(total_consultados),
        "help": f"Total de empresas consultadas em {uf_selecionada}",
    },
    {
        "label": "Sancionadas (CEIS)",
        "valor": formatar_numero(ceis_total),
        "help": "Empresas no Cadastro de Inidoneas e Suspensas",
    },
    {
        "label": "Punidas (CNEP)",
        "valor": formatar_numero(cnep_total),
        "help": "Empresas no Cadastro Nacional de Empresas Punidas",
    },
    {
        "label": "Com Contratos (PNCP)",
        "valor": formatar_numero(pncp_total),
        "help": "Empresas com contratos publicos no PNCP",
    },
])

# === Tabs ===
tab_sancoes, tab_contratos, tab_consumidor, tab_consulta = st.tabs([
    "Sancoes (CEIS/CNEP)",
    "Contratos Publicos (PNCP)",
    "Consumidor.gov.br",
    "Consulta Individual",
])

# --- Tab 1: Sancoes ---
with tab_sancoes:
    st.subheader("Empresas Sancionadas - CEIS/CNEP")

    sancionadas = extrair_empresas_sancionadas(df_compliance)

    if not sancionadas:
        st.info(f"Nenhuma empresa sancionada encontrada em {uf_selecionada}.")
    else:
        df_sancoes = pd.DataFrame(sancionadas)

        # Filtros
        col_tipo, col_orgao = st.columns(2)
        with col_tipo:
            tipos = ["Todos"] + sorted(df_sancoes["tipo"].unique().tolist())
            tipo_sel = st.selectbox("Tipo", tipos, key="tipo_sancao")
        with col_orgao:
            orgaos = ["Todos"] + sorted(df_sancoes["orgao"].dropna().unique().tolist())
            orgao_sel = st.selectbox("Orgao Sancionador", orgaos, key="orgao_sancao")

        df_filtrado = df_sancoes.copy()
        if tipo_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado["tipo"] == tipo_sel]
        if orgao_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado["orgao"] == orgao_sel]

        st.dataframe(
            df_filtrado,
            use_container_width=True,
            hide_index=True,
            column_config={
                "cnpj": st.column_config.TextColumn("CNPJ", width="medium"),
                "nome": st.column_config.TextColumn("Empresa", width="large"),
                "tipo": st.column_config.TextColumn("Cadastro", width="small"),
                "orgao": st.column_config.TextColumn("Orgao", width="large"),
                "tipo_sancao": st.column_config.TextColumn("Tipo Sancao", width="medium"),
                "data_inicio": st.column_config.TextColumn("Inicio", width="small"),
                "data_fim": st.column_config.TextColumn("Fim", width="small"),
                "fundamentacao": st.column_config.TextColumn("Fundamentacao", width="large"),
                "valor_multa": st.column_config.NumberColumn("Multa (R$)", format="R$ %.2f"),
            },
        )

        # Graficos
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            df_por_tipo = df_sancoes.groupby("tipo").size().reset_index(name="total")
            fig = grafico_pizza(df_por_tipo, "total", "tipo", titulo="Sancoes por Cadastro")
            st.plotly_chart(fig, use_container_width=True)

        with col_g2:
            df_por_orgao = (
                df_sancoes.groupby("orgao").size().reset_index(name="total")
                .sort_values("total", ascending=True).tail(10)
            )
            if not df_por_orgao.empty:
                fig = grafico_barras(
                    df_por_orgao, "orgao", "total",
                    titulo="Top Orgaos Sancionadores",
                    horizontal=True, altura=400,
                )
                st.plotly_chart(fig, use_container_width=True)

# --- Tab 2: Contratos PNCP ---
with tab_contratos:
    st.subheader("Contratos Publicos - PNCP")

    contratos = extrair_contratos_pncp(df_compliance)

    if not contratos:
        st.info(f"Nenhum contrato publico encontrado em {uf_selecionada}.")
    else:
        df_contratos = pd.DataFrame(contratos)
        df_contratos["valor"] = pd.to_numeric(df_contratos["valor"], errors="coerce").fillna(0)

        # Metricas
        total_contratos = len(df_contratos)
        valor_total = df_contratos["valor"].sum()
        empresas_unicas = df_contratos["cnpj"].nunique()

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total de Contratos", formatar_numero(total_contratos))
        col_m2.metric("Valor Total", formatar_moeda(valor_total))
        col_m3.metric("Empresas Fornecedoras", formatar_numero(empresas_unicas))

        # Tabela
        st.dataframe(
            df_contratos.sort_values("valor", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "cnpj": st.column_config.TextColumn("CNPJ", width="medium"),
                "nome": st.column_config.TextColumn("Empresa", width="large"),
                "orgao": st.column_config.TextColumn("Orgao Contratante", width="large"),
                "objeto": st.column_config.TextColumn("Objeto", width="large"),
                "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
                "data_inicio": st.column_config.TextColumn("Inicio", width="small"),
                "data_fim": st.column_config.TextColumn("Fim", width="small"),
                "numero": st.column_config.TextColumn("N. Contrato", width="small"),
            },
        )

        # Graficos
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            df_top = (
                df_contratos.groupby(["cnpj", "nome"])["valor"].sum()
                .reset_index().sort_values("valor", ascending=True).tail(10)
            )
            if not df_top.empty:
                fig = grafico_barras(
                    df_top, "nome", "valor",
                    titulo="Top 10 Empresas por Valor",
                    horizontal=True, altura=400,
                )
                st.plotly_chart(fig, use_container_width=True)

        with col_g2:
            df_orgaos = (
                df_contratos.groupby("orgao")["valor"].sum()
                .reset_index().sort_values("valor", ascending=True).tail(10)
            )
            if not df_orgaos.empty:
                fig = grafico_barras(
                    df_orgaos, "orgao", "valor",
                    titulo="Top 10 Orgaos Contratantes",
                    horizontal=True, altura=400,
                )
                st.plotly_chart(fig, use_container_width=True)

# --- Tab 3: Consumidor.gov.br ---
with tab_consumidor:
    _exibir_consumidor()

# --- Tab 4: Consulta Individual ---
with tab_consulta:
    st.subheader("Consultar Empresa por CNPJ")

    cnpj_busca = st.text_input("CNPJ", placeholder="00.000.000/0000-00", key="cnpj_consulta")

    if cnpj_busca:
        resultado = consultar_empresa_compliance(cnpj_busca)
        if resultado:
            _exibir_empresa(resultado)
        else:
            st.warning(
                "Empresa nao encontrada no cache local.\n\n"
                "Consulte via script:\n"
                f"```\npython scripts/buscar_compliance.py --cnpjs {cnpj_busca}\n```"
            )

# === Rodape ===
st.markdown("---")
atualizado = resumo_uf.get("atualizado_em", "N/A")
st.caption(
    f"Fontes: CGU/CEIS, CGU/CNEP, PNCP, Consumidor.gov.br | "
    f"Ultima atualizacao: {atualizado}"
)
