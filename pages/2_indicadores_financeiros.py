"""Página 2 - Indicadores Financeiros da Transpocred."""

import streamlit as st
import pandas as pd

from src.api.bcb import buscar_ifdata_transpocred
from src.utils.constants import TRANSPOCRED_NOME, IFDATA_RELATORIOS, CORES
from src.utils.formatting import formatar_bilhoes, formatar_percentual, formatar_moeda
from src.components.kpi_card import kpi_row
from src.components.charts import grafico_barras, grafico_pizza, grafico_barras_agrupadas

st.header(f"Indicadores Financeiros - {TRANSPOCRED_NOME}")
st.markdown("Detalhamento das operações de crédito, captação, resultado e inadimplência.")


def extrair_valor(df, nome_conta):
    if df.empty:
        return None
    mask = df["NomeConta"].str.contains(nome_conta, case=False, na=False)
    resultado = df.loc[mask, "Valor"]
    return resultado.iloc[0] if not resultado.empty else None


def extrair_contas(df, filtro=None, top_n=None):
    """Extrai contas do DataFrame IF.data, opcionalmente filtrando e limitando."""
    if df.empty:
        return pd.DataFrame()
    resultado = df[["NomeConta", "Valor"]].copy()
    resultado["Valor"] = pd.to_numeric(resultado["Valor"], errors="coerce")
    resultado = resultado.dropna(subset=["Valor"])
    if filtro:
        resultado = resultado[resultado["NomeConta"].str.contains(filtro, case=False, na=False)]
    resultado = resultado.sort_values("Valor", ascending=False)
    if top_n:
        resultado = resultado.head(top_n)
    return resultado


# === Tabs ===
tab_credito, tab_captacao, tab_resultado, tab_inadimplencia = st.tabs(
    ["Crédito", "Captação", "Resultado", "Inadimplência"]
)

# === Tab Crédito ===
with tab_credito:
    st.subheader("Operações de Crédito")

    df_cred_pf = buscar_ifdata_transpocred(IFDATA_RELATORIOS["CREDITO_PF"])
    df_cred_pj = buscar_ifdata_transpocred(IFDATA_RELATORIOS["CREDITO_PJ"])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Crédito Pessoa Física**")
        if not df_cred_pf.empty:
            total_pf = extrair_valor(df_cred_pf, "Total da Carteira")
            if total_pf is not None:
                st.metric("Total Crédito PF", formatar_bilhoes(total_pf * 1000))

            # Mostrar totais por modalidade (Grupo)
            df_mod_pf = df_cred_pf[df_cred_pf["NomeConta"] == "Total"].copy()
            df_mod_pf["Valor"] = pd.to_numeric(df_mod_pf["Valor"], errors="coerce")
            df_mod_pf = df_mod_pf.dropna(subset=["Valor"])
            df_mod_pf = df_mod_pf[df_mod_pf["Valor"] > 0]
            if "Grupo" in df_mod_pf.columns:
                df_mod_pf = df_mod_pf[["Grupo", "Valor"]].rename(columns={"Grupo": "NomeConta"})
            if not df_mod_pf.empty:
                fig = grafico_barras(
                    df_mod_pf.sort_values("Valor", ascending=False),
                    x="NomeConta", y="Valor",
                    titulo="Crédito PF por Modalidade (R$ mil)",
                    cor=CORES["verde_ailos"],
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados de crédito PF não disponíveis.")

    with col2:
        st.markdown("**Crédito Pessoa Jurídica**")
        if not df_cred_pj.empty:
            total_pj = extrair_valor(df_cred_pj, "Total da Carteira")
            if total_pj is not None:
                st.metric("Total Crédito PJ", formatar_bilhoes(total_pj * 1000))

            # Mostrar totais por modalidade (Grupo)
            df_mod_pj = df_cred_pj[df_cred_pj["NomeConta"] == "Total"].copy()
            df_mod_pj["Valor"] = pd.to_numeric(df_mod_pj["Valor"], errors="coerce")
            df_mod_pj = df_mod_pj.dropna(subset=["Valor"])
            df_mod_pj = df_mod_pj[df_mod_pj["Valor"] > 0]
            if "Grupo" in df_mod_pj.columns:
                df_mod_pj = df_mod_pj[["Grupo", "Valor"]].rename(columns={"Grupo": "NomeConta"})
            if not df_mod_pj.empty:
                fig = grafico_barras(
                    df_mod_pj.sort_values("Valor", ascending=False),
                    x="NomeConta", y="Valor",
                    titulo="Crédito PJ por Modalidade (R$ mil)",
                    cor=CORES["azul"],
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados de crédito PJ não disponíveis.")

# === Tab Captação ===
with tab_captacao:
    st.subheader("Captação de Recursos")

    df_captacao = buscar_ifdata_transpocred(IFDATA_RELATORIOS["PASSIVO"])

    if not df_captacao.empty:
        # KPIs de captação
        dep_vista = extrair_valor(df_captacao, "Depositos a Vista")
        dep_prazo = extrair_valor(df_captacao, "Depositos a Prazo")
        dep_poupanca = extrair_valor(df_captacao, "Depositos de Poupanca")

        kpis_cap = []
        if dep_vista is not None:
            kpis_cap.append({"label": "Depósitos à Vista", "valor": formatar_bilhoes(dep_vista * 1000)})
        if dep_prazo is not None:
            kpis_cap.append({"label": "Depósitos a Prazo", "valor": formatar_bilhoes(dep_prazo * 1000)})
        if dep_poupanca is not None:
            kpis_cap.append({"label": "Poupança", "valor": formatar_bilhoes(dep_poupanca * 1000)})
        if kpis_cap:
            kpi_row(kpis_cap)

        # Gráfico composição captação
        df_comp = extrair_contas(df_captacao, top_n=8)
        df_comp = df_comp[df_comp["Valor"] > 0]
        if not df_comp.empty:
            fig = grafico_pizza(
                df_comp, valores="Valor", nomes="NomeConta",
                titulo="Composição da Captação",
            )
            fig.update_layout(
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.15,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=11),
                ),
                margin=dict(b=180),
                height=550,
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Dados de captação não disponíveis.")

# === Tab Resultado ===
with tab_resultado:
    st.subheader("Demonstração de Resultado (DRE)")

    df_dre = buscar_ifdata_transpocred(IFDATA_RELATORIOS["DRE"])

    if not df_dre.empty:
        resultado_liq = extrair_valor(df_dre, "Sobras ou Perdas")
        receitas = extrair_valor(df_dre, "Receitas de Intermediacao")
        despesas = extrair_valor(df_dre, "Despesas de Intermediacao")

        kpis_dre = []
        if resultado_liq is not None:
            kpis_dre.append({
                "label": "Sobras/Perdas",
                "valor": formatar_bilhoes(resultado_liq * 1000),
                "delta_color": "normal" if resultado_liq and resultado_liq > 0 else "inverse",
            })
        if receitas is not None:
            kpis_dre.append({"label": "Receitas de Intermediação", "valor": formatar_bilhoes(receitas * 1000)})
        if despesas is not None:
            kpis_dre.append({"label": "Despesas de Intermediação", "valor": formatar_bilhoes(abs(despesas) * 1000 if despesas else 0)})
        if kpis_dre:
            kpi_row(kpis_dre)

        # Tabela DRE
        df_dre_view = extrair_contas(df_dre)
        if not df_dre_view.empty:
            st.dataframe(
                df_dre_view.rename(columns={"NomeConta": "Conta", "Valor": "Valor (R$ mil)"}),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("Dados de resultado não disponíveis.")

# === Tab Inadimplência ===
with tab_inadimplencia:
    st.subheader("Inadimplência")
    st.markdown(
        "Indicador calculado a partir das operações **vencidas há mais de 15 dias** "
        "em relação ao total da carteira (relatórios 11 e 13 do IF.data)."
    )

    # Usar dados já carregados dos relatórios 11 (PF) e 13 (PJ)
    df_inad_pf = df_cred_pf if not df_cred_pf.empty else pd.DataFrame()
    df_inad_pj = df_cred_pj if not df_cred_pj.empty else pd.DataFrame()

    def _calcular_inadimplencia(df, label):
        """Extrai total da carteira e vencido >15 dias."""
        if df.empty or "NomeConta" not in df.columns:
            return None, None, None
        df = df.copy()
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
        # Total da carteira: linha com Grupo=None e "Total da Carteira" no nome
        total = df[df["NomeConta"].str.contains("Total da Carteira", case=False, na=False)]
        val_total = total["Valor"].dropna().iloc[0] if not total.empty and total["Valor"].dropna().any() else 0
        # Vencido: somar "Vencido a Partir de 15 Dias" de todos os grupos
        vencido = df[df["NomeConta"].str.contains("Vencido", case=False, na=False)]
        val_vencido = vencido["Valor"].dropna().sum() if not vencido.empty else 0
        taxa = (val_vencido / val_total * 100) if val_total > 0 else 0
        return val_vencido, val_total, taxa

    venc_pf, tot_pf, taxa_pf = _calcular_inadimplencia(df_inad_pf, "PF")
    venc_pj, tot_pj, taxa_pj = _calcular_inadimplencia(df_inad_pj, "PJ")

    kpis_inad = []
    if taxa_pf is not None and tot_pf and tot_pf > 0:
        kpis_inad.append({
            "label": "Inadimplência PF",
            "valor": formatar_percentual(taxa_pf),
            "help": "Operações PF vencidas >15 dias / Total carteira PF",
        })
    if taxa_pj is not None and tot_pj and tot_pj > 0:
        kpis_inad.append({
            "label": "Inadimplência PJ",
            "valor": formatar_percentual(taxa_pj),
            "help": "Operações PJ vencidas >15 dias / Total carteira PJ",
        })

    # Taxa combinada
    total_geral = (tot_pf or 0) + (tot_pj or 0)
    vencido_geral = (venc_pf or 0) + (venc_pj or 0)
    if total_geral > 0:
        taxa_geral = vencido_geral / total_geral * 100
        kpis_inad.insert(0, {
            "label": "Inadimplência Total",
            "valor": formatar_percentual(taxa_geral),
            "help": "Operações vencidas >15 dias / Total da carteira",
        })

    if kpis_inad:
        kpi_row(kpis_inad)
    else:
        st.info("Dados de inadimplência não disponíveis.")

    # Composição da carteira PF por prazo
    if not df_inad_pf.empty:
        df_pf_view = extrair_contas(df_inad_pf)
        df_pf_view = df_pf_view[df_pf_view["Valor"] > 0]
        if not df_pf_view.empty:
            fig = grafico_barras(
                df_pf_view, x="NomeConta", y="Valor",
                titulo="Carteira de Crédito PF por Prazo (R$ mil)",
                cor=CORES["verde_ailos"],
            )
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
with st.expander("Sobre os dados"):
    st.markdown("""
**Fonte dos dados:** Banco Central do Brasil — IF.data (Sistema de Informações de Instituições Financeiras)

**API utilizada:** OLINDA/BCB — Relatórios 3 (Passivo), 4 (DRE), 11 (Crédito PF) e 13 (Crédito PJ)

**Principais métricas:**
- Depósitos (à vista, a prazo, poupança) e composição da captação
- Receitas e Despesas de Intermediação, Sobras/Perdas (DRE)
- Crédito PF e PJ por modalidade
- Inadimplência: operações vencidas há mais de 15 dias (PF e PJ)

**Periodicidade:** Trimestral (último trimestre disponível)

**Atualização do dashboard:** Semanal (GitHub Actions) ou manual via `scripts/atualizar_dados.py`.
""")
