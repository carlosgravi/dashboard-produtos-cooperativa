"""Página 12 - Market Share e Tendências de Mercado."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.api.bcb import buscar_ifdata_valores, buscar_ifdata_evolucao

try:
    from src.api.bcb import carregar_ranking_historico
except ImportError:
    def carregar_ranking_historico():
        return None
from src.utils.constants import (
    TRANSPOCRED_CNPJ_8, TRANSPOCRED_NOME, IFDATA_RELATORIOS,
    CORES, PALETA_SEQUENCIAL, LAYOUT_PADRAO,
)
from src.utils.formatting import formatar_bilhoes, formatar_percentual, formatar_numero
from src.components.kpi_card import kpi_row

st.header("Market Share e Tendências")
st.markdown(
    f"Participação de mercado e evolução da **{TRANSPOCRED_NOME}** "
    "no universo de cooperativas singulares de crédito."
)

# === Métricas-chave do relatório 1 ===
METRICAS = {
    "Ativo Total": "Ativo Total",
    "Operações de Crédito": "Operações de Crédito",
    "Depósitos Totais": "Depósitos Totais",
    "Patrimônio Líquido": "Patrimônio Líquido",
}

# Alternativas de nome que a API pode retornar
METRICAS_ALIAS = {
    "Ativo Total": ["Ativo Total"],
    "Operações de Crédito": ["Operações de Crédito", "Operacoes de Credito",
                              "Carteira de Crédito", "Carteira de Credito"],
    "Depósitos Totais": ["Depósitos Totais", "Depositos Totais",
                          "Captação Total", "Captacao Total",
                          "Depósitos", "Depositos"],
    "Patrimônio Líquido": ["Patrimônio Líquido", "Patrimonio Liquido"],
}


def _filtrar_metrica(df, nome_metrica):
    """Filtra DataFrame por nome de conta, tentando aliases."""
    aliases = METRICAS_ALIAS.get(nome_metrica, [nome_metrica])
    for alias in aliases:
        mask = df["NomeConta"].str.contains(alias, case=False, na=False)
        if mask.any():
            return df[mask].copy()
    return pd.DataFrame()


def _encontrar_transpocred(df):
    """Retorna mask booleana para linhas da Transpocred."""
    if "CodInst" in df.columns:
        return df["CodInst"].astype(str).str.replace(r"\D", "", regex=True) == TRANSPOCRED_CNPJ_8
    if "NomeInstituicao" in df.columns:
        return df["NomeInstituicao"].str.contains("TRANSPOCRED", case=False, na=False)
    return pd.Series([False] * len(df))


# ============================================================
# Tabs
# ============================================================
tab1, tab2, tab3 = st.tabs([
    "Market Share (Snapshot)",
    "Tendências (Evolução)",
    "Evolução do Market Share",
])

# ============================================================
# TAB 1 — Market Share (snapshot atual)
# ============================================================
with tab1:
    df_todas = buscar_ifdata_valores(
        relatorio=IFDATA_RELATORIOS["RESUMO"],
        cnpj_8=None,
        tipo_instituicao=3,
        timeout=300,
    )

    if df_todas.empty:
        st.error(
            "Não foi possível carregar os dados das cooperativas. "
            "Tente novamente mais tarde."
        )
    else:
        # Normalizar Valor
        if "Valor" not in df_todas.columns and "Saldo" in df_todas.columns:
            df_todas["Valor"] = pd.to_numeric(df_todas["Saldo"], errors="coerce")

        # === KPIs de Market Share ===
        kpis_share = []
        shares = {}
        for nome_metrica in METRICAS:
            df_m = _filtrar_metrica(df_todas, nome_metrica)
            if df_m.empty:
                continue
            df_m["Valor"] = pd.to_numeric(df_m["Valor"], errors="coerce")
            df_m = df_m.dropna(subset=["Valor"])

            total_mercado = df_m["Valor"].sum()
            mask_t = _encontrar_transpocred(df_m)
            valor_t = df_m.loc[mask_t, "Valor"].sum() if mask_t.any() else 0

            if total_mercado > 0 and valor_t > 0:
                share = (valor_t / total_mercado) * 100
                shares[nome_metrica] = share
                kpis_share.append({
                    "label": f"Share {nome_metrica}",
                    "valor": formatar_percentual(share),
                    "help": f"{formatar_bilhoes(valor_t * 1000)} de {formatar_bilhoes(total_mercado * 1000)}",
                })

        if kpis_share:
            kpi_row(kpis_share)
        else:
            st.warning("Não foi possível calcular market share. Dados da Transpocred não encontrados.")

        st.markdown("---")

        # === Gráfico Pizza: Top 10 + Outras (por Ativo Total) ===
        st.subheader("Composição do Mercado — Ativo Total")

        df_ativo = _filtrar_metrica(df_todas, "Ativo Total")
        if not df_ativo.empty:
            df_ativo["Valor"] = pd.to_numeric(df_ativo["Valor"], errors="coerce")
            df_ativo = df_ativo.dropna(subset=["Valor"])

            # Identificar coluna de nome
            col_nome = None
            for c in ["NomeInstituicao", "NomeInst", "Instituicao", "Nome"]:
                if c in df_ativo.columns:
                    col_nome = c
                    break

            df_ativo_sorted = df_ativo.sort_values("Valor", ascending=False).reset_index(drop=True)

            # Top 10 + Outras
            top10 = df_ativo_sorted.head(10).copy()
            outras_valor = df_ativo_sorted.iloc[10:]["Valor"].sum() if len(df_ativo_sorted) > 10 else 0

            if col_nome:
                import re

                def _nome_curto(nome):
                    if " - " in str(nome):
                        candidato = str(nome).split(" - ")[-1].strip()
                        if len(candidato) >= 3:
                            return candidato[:30]
                    limpo = re.sub(
                        r"COOPERATIVA\s+(CENTRAL\s+)?(DE\s+)?(ECONOMIA\s+E\s+)?(CR[EÉ]DITO|CREDITO)\s*,?\s*",
                        "", str(nome), flags=re.IGNORECASE,
                    )
                    limpo = re.sub(r",?\s*POUPAN[CÇ]A\s+E\s+INVESTIMENTO", "", limpo, flags=re.IGNORECASE)
                    limpo = re.sub(r"\s*-?\s*LTDA\.?", "", limpo, flags=re.IGNORECASE)
                    return limpo.strip(" -,")[:30]

                top10["Label"] = top10[col_nome].apply(_nome_curto)
            else:
                top10["Label"] = [f"#{i+1}" for i in range(len(top10))]

            # Montar DataFrame para pizza
            df_pizza = pd.DataFrame({
                "Nome": list(top10["Label"]) + (["Outras"] if outras_valor > 0 else []),
                "Valor": list(top10["Valor"]) + ([outras_valor] if outras_valor > 0 else []),
            })

            # Criar coluna formatada para hover
            df_pizza["Valor_Fmt"] = df_pizza["Valor"].apply(lambda v: formatar_bilhoes(v * 1000))

            fig_pizza = px.pie(
                df_pizza, values="Valor", names="Nome",
                color_discrete_sequence=PALETA_SEQUENCIAL,
                hole=0.4,
            )
            fig_pizza.update_traces(
                textposition="inside",
                textinfo="percent",
                hovertemplate="<b>%{label}</b><br>%{percent}<br>%{customdata[0]}<extra></extra>",
                customdata=df_pizza[["Valor_Fmt"]].values,
            )
            layout_pizza = dict(LAYOUT_PADRAO)
            layout_pizza["height"] = 450
            layout_pizza["title"] = dict(text="Top 10 Cooperativas + Outras — Ativo Total", x=0.5)
            layout_pizza["legend"] = dict(
                orientation="h",
                yanchor="top",
                y=-0.05,
                xanchor="center",
                x=0.5,
            )
            layout_pizza["margin"] = dict(l=20, r=20, t=50, b=10)
            fig_pizza.update_layout(**layout_pizza)
            st.plotly_chart(fig_pizza, use_container_width=True)

        # === Tabela: Posição em cada métrica ===
        st.subheader(f"Posição da {TRANSPOCRED_NOME} por Métrica")

        posicoes = []
        for nome_metrica in METRICAS:
            df_m = _filtrar_metrica(df_todas, nome_metrica)
            if df_m.empty:
                continue
            df_m["Valor"] = pd.to_numeric(df_m["Valor"], errors="coerce")
            df_m = df_m.dropna(subset=["Valor"])
            df_m = df_m.sort_values("Valor", ascending=False).reset_index(drop=True)
            df_m["Posição"] = range(1, len(df_m) + 1)

            mask_t = _encontrar_transpocred(df_m)
            if mask_t.any():
                idx = df_m[mask_t].index[0]
                posicoes.append({
                    "Métrica": nome_metrica,
                    "Posição": f"{df_m.loc[idx, 'Posição']}º",
                    "Valor": formatar_bilhoes(df_m.loc[idx, "Valor"] * 1000),
                    "Total Cooperativas": formatar_numero(len(df_m)),
                    "Share (%)": formatar_percentual(shares.get(nome_metrica, 0)),
                })

        if posicoes:
            st.dataframe(
                pd.DataFrame(posicoes),
                use_container_width=True,
                hide_index=True,
            )

        # === Concentração: Top 5 / Top 10 / Top 20 ===
        st.subheader("Concentração de Mercado")

        concentracoes = []
        for nome_metrica in METRICAS:
            df_m = _filtrar_metrica(df_todas, nome_metrica)
            if df_m.empty:
                continue
            df_m["Valor"] = pd.to_numeric(df_m["Valor"], errors="coerce")
            df_m = df_m.dropna(subset=["Valor"])
            df_m = df_m.sort_values("Valor", ascending=False)
            total = df_m["Valor"].sum()

            if total > 0:
                concentracoes.append({
                    "Métrica": nome_metrica,
                    "Top 5": formatar_percentual(df_m.head(5)["Valor"].sum() / total * 100, 1),
                    "Top 10": formatar_percentual(df_m.head(10)["Valor"].sum() / total * 100, 1),
                    "Top 20": formatar_percentual(df_m.head(20)["Valor"].sum() / total * 100, 1),
                })

        if concentracoes:
            st.dataframe(
                pd.DataFrame(concentracoes),
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# TAB 2 — Tendências (evolução Transpocred)
# ============================================================
with tab2:
    df_evolucao = buscar_ifdata_evolucao(
        relatorio=IFDATA_RELATORIOS["RESUMO"],
        cnpj_8=TRANSPOCRED_CNPJ_8,
        n_trimestres=12,
    )

    if df_evolucao.empty:
        st.error("Não foi possível carregar dados de evolução da Transpocred.")
    else:
        if "Valor" not in df_evolucao.columns and "Saldo" in df_evolucao.columns:
            df_evolucao["Valor"] = pd.to_numeric(df_evolucao["Saldo"], errors="coerce")

        # Pivotar: uma linha por trimestre, colunas = métricas
        dfs_metricas = {}
        for nome_metrica in METRICAS:
            df_m = _filtrar_metrica(df_evolucao, nome_metrica)
            if not df_m.empty:
                df_m["Valor"] = pd.to_numeric(df_m["Valor"], errors="coerce")
                pivot = df_m.groupby("DataBase")["Valor"].sum().reset_index()
                pivot = pivot.rename(columns={"Valor": nome_metrica})
                dfs_metricas[nome_metrica] = pivot

        if dfs_metricas:
            # Merge em um único DataFrame
            df_trend = None
            for nome, df_m in dfs_metricas.items():
                if df_trend is None:
                    df_trend = df_m
                else:
                    df_trend = pd.merge(df_trend, df_m, on="DataBase", how="outer")

            df_trend = df_trend.sort_values("DataBase").reset_index(drop=True)
            # Formatar período: "202509" -> "09/2025"
            df_trend["Periodo"] = df_trend["DataBase"].apply(
                lambda d: f"{d[4:6]}/{d[:4]}" if len(str(d)) == 6 else d
            )
            n_trimestres = len(df_trend)

            # === KPIs: CAGR anualizado ===
            kpis_cagr = []
            for nome_metrica in METRICAS:
                if nome_metrica not in df_trend.columns:
                    continue
                serie = df_trend[nome_metrica].dropna()
                if len(serie) >= 2:
                    v_ini = serie.iloc[0]
                    v_fin = serie.iloc[-1]
                    n = len(serie) - 1
                    if v_ini > 0 and n > 0:
                        cagr = (v_fin / v_ini) ** (4 / n) - 1  # Anualizado (4 trim/ano)
                        kpis_cagr.append({
                            "label": f"CAGR {nome_metrica}",
                            "valor": formatar_percentual(cagr * 100, 1),
                            "help": f"Crescimento anualizado em {n} trimestres",
                        })

            if kpis_cagr:
                kpi_row(kpis_cagr)

            st.markdown("---")

            # === Gráfico linhas múltiplas: evolução absoluta ===
            st.subheader("Evolução Trimestral")

            metricas_disponiveis = [m for m in METRICAS if m in df_trend.columns]
            fig_evo = go.Figure()
            for i, metrica in enumerate(metricas_disponiveis):
                valores_fmt = [formatar_bilhoes(v * 1000) for v in df_trend[metrica]]
                fig_evo.add_trace(go.Scatter(
                    x=df_trend["Periodo"],
                    y=df_trend[metrica],
                    mode="lines+markers",
                    name=metrica,
                    line=dict(color=PALETA_SEQUENCIAL[i % len(PALETA_SEQUENCIAL)], width=2),
                    marker=dict(size=5),
                    customdata=valores_fmt,
                    hovertemplate="<b>" + metrica + "</b><br>Trimestre: %{x}<br>Valor: %{customdata}<extra></extra>",
                ))
            layout_evo = dict(LAYOUT_PADRAO)
            layout_evo["title"] = dict(text=f"Evolução {TRANSPOCRED_NOME} (R$ mil)", x=0.5)
            layout_evo["height"] = 450
            layout_evo["yaxis"] = dict(tickformat=",")
            layout_evo["xaxis"] = dict(
                type="category",
                categoryorder="array",
                categoryarray=list(df_trend["Periodo"]),
            )
            fig_evo.update_layout(**layout_evo)
            st.plotly_chart(fig_evo, use_container_width=True)

            # === Gráfico barras: crescimento % trimestre a trimestre ===
            st.subheader("Crescimento Trimestral (%)")

            metrica_sel = st.selectbox(
                "Métrica",
                metricas_disponiveis,
                key="trend_metrica",
            )

            if metrica_sel and metrica_sel in df_trend.columns:
                df_cresc = df_trend[["Periodo", metrica_sel]].dropna().copy()
                df_cresc["Crescimento (%)"] = df_cresc[metrica_sel].pct_change() * 100

                df_cresc_plot = df_cresc.dropna(subset=["Crescimento (%)"])
                if not df_cresc_plot.empty:
                    cores_cresc = [
                        CORES["verde_ailos"] if v >= 0 else CORES["vermelho"]
                        for v in df_cresc_plot["Crescimento (%)"]
                    ]
                    valores_cresc_fmt = [formatar_bilhoes(v * 1000) for v in df_cresc_plot[metrica_sel]]
                    fig_cresc = go.Figure()
                    fig_cresc.add_trace(go.Bar(
                        x=df_cresc_plot["Periodo"],
                        y=df_cresc_plot["Crescimento (%)"],
                        marker_color=cores_cresc,
                        text=[f"{v:+.1f}%" for v in df_cresc_plot["Crescimento (%)"]],
                        textposition="outside",
                        customdata=valores_cresc_fmt,
                        hovertemplate="<b>%{x}</b><br>Crescimento: %{y:+.2f}%<br>Valor: %{customdata}<extra></extra>",
                    ))
                    layout_cresc = dict(LAYOUT_PADRAO)
                    layout_cresc["title"] = dict(
                        text=f"Crescimento Trimestral — {metrica_sel}", x=0.5,
                    )
                    layout_cresc["height"] = 400
                    fig_cresc.update_layout(**layout_cresc)
                    st.plotly_chart(fig_cresc, use_container_width=True)

            # === Indicadores: Alavancagem e Eficiência ===
            st.subheader("Indicadores Derivados")

            indicadores = []
            if "Ativo Total" in df_trend.columns and "Patrimônio Líquido" in df_trend.columns:
                df_trend["Alavancagem"] = df_trend["Ativo Total"] / df_trend["Patrimônio Líquido"]
                indicadores.append("Alavancagem")

            if "Operações de Crédito" in df_trend.columns and "Depósitos Totais" in df_trend.columns:
                df_trend["Eficiência (Crédito/Captação)"] = (
                    df_trend["Operações de Crédito"] / df_trend["Depósitos Totais"]
                )
                indicadores.append("Eficiência (Crédito/Captação)")

            if indicadores:
                fig_ind = go.Figure()
                for i, ind in enumerate(indicadores):
                    if "Alavancagem" in ind:
                        hover_fmt = "<b>%{x}</b><br>Alavancagem: %{y:.2f}x<extra></extra>"
                    else:
                        hover_fmt = "<b>%{x}</b><br>Eficiência: %{y:.1%}<extra></extra>"
                    fig_ind.add_trace(go.Scatter(
                        x=df_trend["Periodo"],
                        y=df_trend[ind],
                        mode="lines+markers",
                        name=ind,
                        line=dict(
                            color=PALETA_SEQUENCIAL[(i + 4) % len(PALETA_SEQUENCIAL)],
                            width=2,
                        ),
                        marker=dict(size=5),
                        hovertemplate=hover_fmt,
                    ))
                layout_ind = dict(LAYOUT_PADRAO)
                layout_ind["title"] = dict(text="Alavancagem e Eficiência", x=0.5)
                layout_ind["height"] = 400
                fig_ind.update_layout(**layout_ind)
                st.plotly_chart(fig_ind, use_container_width=True)

                # KPIs últimos valores
                ultimo = df_trend.iloc[-1]
                kpis_ind = []
                if "Alavancagem" in indicadores:
                    kpis_ind.append({
                        "label": "Alavancagem (Ativo/PL)",
                        "valor": f"{ultimo['Alavancagem']:.2f}x",
                        "help": "Ativo Total / Patrimônio Líquido",
                    })
                if "Eficiência (Crédito/Captação)" in indicadores:
                    kpis_ind.append({
                        "label": "Eficiência (Crédito/Captação)",
                        "valor": formatar_percentual(ultimo["Eficiência (Crédito/Captação)"] * 100, 1),
                        "help": "Operações de Crédito / Depósitos Totais",
                    })
                if kpis_ind:
                    kpi_row(kpis_ind)
        else:
            st.warning("Nenhuma métrica encontrada nos dados de evolução.")


# ============================================================
# TAB 3 — Evolução do Market Share (histórico)
# ============================================================
with tab3:
    df_historico = carregar_ranking_historico()

    if df_historico is None:
        st.info(
            "Dados de ranking histórico não disponíveis. "
            "Para coletar, execute:\n\n"
            "```\npython scripts/atualizar_dados.py --ranking-historico\n```\n\n"
            "Isso busca o ranking de todas as cooperativas para os últimos 8 trimestres (~40 min)."
        )
    else:
        if "Valor" not in df_historico.columns and "Saldo" in df_historico.columns:
            df_historico["Valor"] = pd.to_numeric(df_historico["Saldo"], errors="coerce")

        trimestres = sorted(df_historico["DataBase"].unique())
        st.caption(f"Trimestres disponíveis: {', '.join(trimestres)}")

        metrica_hist = st.selectbox(
            "Métrica",
            list(METRICAS.keys()),
            key="hist_metrica",
        )

        df_m_hist = _filtrar_metrica(df_historico, metrica_hist)

        if df_m_hist.empty:
            st.warning(f"Métrica '{metrica_hist}' não encontrada nos dados históricos.")
        else:
            df_m_hist["Valor"] = pd.to_numeric(df_m_hist["Valor"], errors="coerce")
            df_m_hist = df_m_hist.dropna(subset=["Valor"])

            # Calcular share e posição por trimestre
            evolucao_share = []
            for dt in trimestres:
                df_dt = df_m_hist[df_m_hist["DataBase"] == dt].copy()
                if df_dt.empty:
                    continue

                total = df_dt["Valor"].sum()
                df_dt = df_dt.sort_values("Valor", ascending=False).reset_index(drop=True)
                df_dt["Posição"] = range(1, len(df_dt) + 1)

                mask_t = _encontrar_transpocred(df_dt)
                if mask_t.any():
                    idx = df_dt[mask_t].index[0]
                    valor_t = df_dt.loc[idx, "Valor"]
                    share = (valor_t / total * 100) if total > 0 else 0
                    evolucao_share.append({
                        "Trimestre": f"{dt[4:6]}/{dt[:4]}" if len(str(dt)) == 6 else dt,
                        "Share (%)": share,
                        "Posição": df_dt.loc[idx, "Posição"],
                        "Valor Transpocred": valor_t,
                        "Total Mercado": total,
                        "Nº Cooperativas": len(df_dt),
                    })

            if not evolucao_share:
                st.warning("Transpocred não encontrada nos dados históricos.")
            else:
                df_evo_share = pd.DataFrame(evolucao_share)

                # === Gráfico: Share % ao longo dos trimestres ===
                st.subheader(f"Evolução do Market Share — {metrica_hist}")

                share_custom = list(zip(
                    [formatar_bilhoes(v * 1000) for v in df_evo_share["Valor Transpocred"]],
                    [formatar_bilhoes(v * 1000) for v in df_evo_share["Total Mercado"]],
                ))
                fig_share = go.Figure()
                fig_share.add_trace(go.Scatter(
                    x=df_evo_share["Trimestre"],
                    y=df_evo_share["Share (%)"],
                    mode="lines+markers+text",
                    name="Market Share (%)",
                    line=dict(color=CORES["verde_ailos"], width=3),
                    marker=dict(size=8),
                    text=[f"{v:.2f}%" for v in df_evo_share["Share (%)"]],
                    textposition="top center",
                    customdata=share_custom,
                    hovertemplate=(
                        "<b>Trimestre: %{x}</b><br>"
                        "Share: %{y:.2f}%<br>"
                        "Transpocred: %{customdata[0]}<br>"
                        "Total Mercado: %{customdata[1]}"
                        "<extra></extra>"
                    ),
                ))
                layout_share = dict(LAYOUT_PADRAO)
                layout_share["title"] = dict(
                    text=f"Market Share {TRANSPOCRED_NOME} — {metrica_hist}", x=0.5,
                )
                layout_share["height"] = 400
                layout_share["yaxis"] = dict(title="Share (%)", ticksuffix="%")
                fig_share.update_layout(**layout_share)
                st.plotly_chart(fig_share, use_container_width=True)

                # === Gráfico: Posição no ranking ===
                st.subheader(f"Posição no Ranking — {metrica_hist}")

                pos_custom = list(zip(
                    df_evo_share["Nº Cooperativas"].astype(int),
                    [formatar_bilhoes(v * 1000) for v in df_evo_share["Valor Transpocred"]],
                ))
                fig_pos = go.Figure()
                fig_pos.add_trace(go.Scatter(
                    x=df_evo_share["Trimestre"],
                    y=df_evo_share["Posição"],
                    mode="lines+markers+text",
                    name="Posição",
                    line=dict(color=CORES["azul"], width=3),
                    marker=dict(size=8),
                    text=[f"{int(v)}º" for v in df_evo_share["Posição"]],
                    textposition="top center",
                    customdata=pos_custom,
                    hovertemplate=(
                        "<b>Trimestre: %{x}</b><br>"
                        "Posição: %{y}º de %{customdata[0]}<br>"
                        "Valor: %{customdata[1]}"
                        "<extra></extra>"
                    ),
                ))
                layout_pos = dict(LAYOUT_PADRAO)
                layout_pos["title"] = dict(
                    text=f"Posição no Ranking — {metrica_hist}", x=0.5,
                )
                layout_pos["height"] = 400
                layout_pos["yaxis"] = dict(
                    title="Posição", autorange="reversed",
                )
                fig_pos.update_layout(**layout_pos)
                st.plotly_chart(fig_pos, use_container_width=True)

                # === Comparação: crescimento Transpocred vs mercado ===
                st.subheader("Crescimento: Transpocred vs Mercado Total")

                if len(df_evo_share) >= 2:
                    v_ini_t = df_evo_share.iloc[0]["Valor Transpocred"]
                    v_fin_t = df_evo_share.iloc[-1]["Valor Transpocred"]
                    v_ini_m = df_evo_share.iloc[0]["Total Mercado"]
                    v_fin_m = df_evo_share.iloc[-1]["Total Mercado"]

                    cresc_t = ((v_fin_t / v_ini_t) - 1) * 100 if v_ini_t > 0 else 0
                    cresc_m = ((v_fin_m / v_ini_m) - 1) * 100 if v_ini_m > 0 else 0

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            f"Crescimento {TRANSPOCRED_NOME}",
                            formatar_percentual(cresc_t, 1),
                            help=f"De {formatar_bilhoes(v_ini_t * 1000)} para {formatar_bilhoes(v_fin_t * 1000)}",
                        )
                    with col2:
                        st.metric(
                            "Crescimento Total do Mercado",
                            formatar_percentual(cresc_m, 1),
                            help=f"De {formatar_bilhoes(v_ini_m * 1000)} para {formatar_bilhoes(v_fin_m * 1000)}",
                        )

                    # Gráfico de barras comparativo
                    df_comp = pd.DataFrame({
                        "": [TRANSPOCRED_NOME, "Mercado Total"],
                        "Crescimento (%)": [cresc_t, cresc_m],
                    })
                    df_comp["De"] = [formatar_bilhoes(v_ini_t * 1000), formatar_bilhoes(v_ini_m * 1000)]
                    df_comp["Para"] = [formatar_bilhoes(v_fin_t * 1000), formatar_bilhoes(v_fin_m * 1000)]
                    fig_comp = px.bar(
                        df_comp, x="", y="Crescimento (%)",
                        color="",
                        color_discrete_map={
                            TRANSPOCRED_NOME: CORES["verde_ailos"],
                            "Mercado Total": CORES["azul"],
                        },
                        text=[f"{v:+.1f}%" for v in df_comp["Crescimento (%)"]],
                        custom_data=["De", "Para"],
                    )
                    fig_comp.update_traces(
                        textposition="outside",
                        hovertemplate=(
                            "<b>%{x}</b><br>"
                            "Crescimento: %{y:+.1f}%<br>"
                            "De: %{customdata[0]}<br>"
                            "Para: %{customdata[1]}"
                            "<extra></extra>"
                        ),
                    )
                    layout_comp = dict(LAYOUT_PADRAO)
                    layout_comp["title"] = dict(
                        text=f"Crescimento no Período — {metrica_hist}", x=0.5,
                    )
                    layout_comp["height"] = 400
                    layout_comp["showlegend"] = False
                    fig_comp.update_layout(**layout_comp)
                    st.plotly_chart(fig_comp, use_container_width=True)

                # Tabela com dados
                with st.expander("Ver dados"):
                    df_exibir = df_evo_share.copy()
                    df_exibir["Share (%)"] = df_exibir["Share (%)"].apply(
                        lambda v: formatar_percentual(v)
                    )
                    df_exibir["Valor Transpocred"] = df_exibir["Valor Transpocred"].apply(
                        lambda v: formatar_bilhoes(v * 1000)
                    )
                    df_exibir["Total Mercado"] = df_exibir["Total Mercado"].apply(
                        lambda v: formatar_bilhoes(v * 1000)
                    )
                    df_exibir["Posição"] = df_exibir["Posição"].apply(lambda v: f"{int(v)}º")
                    st.dataframe(df_exibir, use_container_width=True, hide_index=True)


# === Sobre os dados ===
st.markdown("---")
with st.expander("Sobre os dados"):
    st.markdown("""
**Fonte dos dados:** Banco Central do Brasil — IF.data (Sistema de Informações de Instituições Financeiras)

**API utilizada:** OLINDA/BCB — Relatório 1 (Resumo), filtro TipoInstituicao=3 (cooperativas individuais)

**Principais métricas:**
- **Market Share:** participação percentual da Transpocred no total de cooperativas
- **CAGR:** taxa de crescimento anual composta, calculada como (V_final / V_inicial)^(4/n_trimestres) − 1
- **Alavancagem:** Ativo Total / Patrimônio Líquido
- **Eficiência:** Operações de Crédito / Depósitos Totais
- **Concentração:** soma dos Top N / total do mercado

**Periodicidade:** Trimestral (snapshot e tendências) / Histórico sob demanda

**Atualização:** Semanal (GitHub Actions) para snapshot e evolução. Ranking histórico: manual via `scripts/atualizar_dados.py --ranking-historico`.
""")
