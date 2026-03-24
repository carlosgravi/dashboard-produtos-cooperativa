"""Pagina 4 - Comparativo de Mercado: Ranking entre cooperativas."""

import streamlit as st
import pandas as pd

from src.api.bcb import buscar_ifdata_valores
from src.utils.constants import TRANSPOCRED_CNPJ_8, TRANSPOCRED_NOME, IFDATA_RELATORIOS, CORES
from src.utils.formatting import formatar_bilhoes, formatar_numero, formatar_percentual
from src.components.kpi_card import kpi_row
from src.components.charts import grafico_barras

st.header("Comparativo de Mercado")
st.markdown(
    f"Posicionamento da **{TRANSPOCRED_NOME}** no ranking de cooperativas singulares de credito."
)

# === Carregar dados completos (sem filtro de CNPJ) ===
df_todas = buscar_ifdata_valores(
    relatorio=IFDATA_RELATORIOS["RESUMO"],
    cnpj_8=None,
    tipo_instituicao="Cooperativas",
    timeout=300,
)

if df_todas.empty:
    st.error(
        "Nao foi possivel carregar os dados completos das cooperativas. "
        "Isso pode acontecer por timeout na API do BCB. Tente novamente mais tarde."
    )
    st.stop()

# === Preparar dados ===
# Filtrar Ativo Total
df_ativo = df_todas[
    df_todas["NomeConta"].str.contains("Ativo Total", case=False, na=False)
].copy()

if df_ativo.empty:
    st.warning("Dados de Ativo Total nao encontrados. Verificando contas disponiveis...")
    if "NomeConta" in df_todas.columns:
        contas = df_todas["NomeConta"].unique()
        st.write("Contas disponiveis:", contas[:20])
    st.stop()

df_ativo["Valor"] = pd.to_numeric(df_ativo["Valor"], errors="coerce")
df_ativo = df_ativo.dropna(subset=["Valor"])

# Identificar coluna de nome da instituicao
col_nome = None
for c in ["NomeInst", "Instituicao", "Nome", "RazaoSocial"]:
    if c in df_ativo.columns:
        col_nome = c
        break
col_cod = "CodInst" if "CodInst" in df_ativo.columns else None

# === Ranking ===
df_ranking = df_ativo.sort_values("Valor", ascending=False).reset_index(drop=True)
df_ranking["Posicao"] = range(1, len(df_ranking) + 1)

# Encontrar Transpocred
mask_transp = pd.Series([False] * len(df_ranking))
if col_cod:
    mask_transp = df_ranking[col_cod].astype(str).str.replace(r"\D", "", regex=True) == TRANSPOCRED_CNPJ_8
elif col_nome:
    mask_transp = df_ranking[col_nome].str.contains("TRANSPOCRED", case=False, na=False)

posicao_transp = None
valor_transp = None
if mask_transp.any():
    idx = df_ranking[mask_transp].index[0]
    posicao_transp = df_ranking.loc[idx, "Posicao"]
    valor_transp = df_ranking.loc[idx, "Valor"]

total_coops = len(df_ranking)
media_ativo = df_ranking["Valor"].mean()
mediana_ativo = df_ranking["Valor"].median()

# === KPIs ===
kpis = [
    {"label": "Total de Cooperativas", "valor": formatar_numero(total_coops)},
]
if posicao_transp is not None:
    kpis.append({
        "label": f"Posicao {TRANSPOCRED_NOME}",
        "valor": f"{posicao_transp}o de {total_coops}",
        "help": "Ranking por Ativo Total",
    })
if valor_transp is not None:
    kpis.append({
        "label": f"Ativo Total {TRANSPOCRED_NOME}",
        "valor": formatar_bilhoes(valor_transp * 1000),
    })
kpis.append({
    "label": "Media do Setor",
    "valor": formatar_bilhoes(media_ativo * 1000),
    "help": "Media de Ativo Total entre cooperativas",
})

kpi_row(kpis)

st.markdown("---")

# === Top 20 com destaque Transpocred ===
st.subheader("Top 20 Cooperativas por Ativo Total")

df_top20 = df_ranking.head(20).copy()
if col_nome:
    df_top20["Label"] = df_top20[col_nome].str[:30]
elif col_cod:
    df_top20["Label"] = df_top20[col_cod]
else:
    df_top20["Label"] = df_top20["Posicao"].astype(str)

# Cores: verde para Transpocred, cinza para outros
cores_barras = []
for _, row in df_top20.iterrows():
    is_transp = False
    if col_cod:
        is_transp = str(row.get(col_cod, "")).replace(".", "").replace("/", "").replace("-", "") == TRANSPOCRED_CNPJ_8
    elif col_nome:
        is_transp = "TRANSPOCRED" in str(row.get(col_nome, "")).upper()
    cores_barras.append(CORES["verde_ailos"] if is_transp else CORES["cinza_claro"])

import plotly.graph_objects as go
from src.utils.constants import LAYOUT_PADRAO

fig = go.Figure()
fig.add_trace(go.Bar(
    x=df_top20["Label"],
    y=df_top20["Valor"],
    marker_color=cores_barras,
    text=[formatar_bilhoes(v * 1000) for v in df_top20["Valor"]],
    textposition="outside",
))
layout = dict(LAYOUT_PADRAO)
layout["title"] = dict(text="Top 20 Cooperativas - Ativo Total (R$ mil)", x=0.5)
layout["height"] = 500
layout["xaxis"] = dict(tickangle=-45)
fig.update_layout(**layout)
st.plotly_chart(fig, use_container_width=True)

# === Transpocred vs Media vs Mediana ===
st.subheader(f"{TRANSPOCRED_NOME} vs Setor")

if valor_transp is not None:
    df_comp = pd.DataFrame({
        "Indicador": [TRANSPOCRED_NOME, "Media do Setor", "Mediana do Setor"],
        "Valor": [valor_transp, media_ativo, mediana_ativo],
    })

    import plotly.express as px
    fig_comp = px.bar(
        df_comp, x="Indicador", y="Valor",
        color="Indicador",
        color_discrete_map={
            TRANSPOCRED_NOME: CORES["verde_ailos"],
            "Media do Setor": CORES["azul"],
            "Mediana do Setor": CORES["laranja"],
        },
        text=[formatar_bilhoes(v * 1000) for v in df_comp["Valor"]],
    )
    fig_comp.update_traces(textposition="outside")
    fig_comp.update_layout(**{**LAYOUT_PADRAO, "height": 400, "showlegend": False})
    fig_comp.update_layout(title=dict(text="Ativo Total - Comparativo (R$ mil)", x=0.5))
    st.plotly_chart(fig_comp, use_container_width=True)

# === Tabela completa (expansivel) ===
with st.expander("Ver ranking completo"):
    colunas_exibir = ["Posicao"]
    if col_nome:
        colunas_exibir.append(col_nome)
    if col_cod:
        colunas_exibir.append(col_cod)
    colunas_exibir.append("Valor")

    st.dataframe(
        df_ranking[colunas_exibir].rename(columns={"Valor": "Ativo Total (R$ mil)"}),
        use_container_width=True,
        hide_index=True,
        height=400,
    )

st.markdown("---")
st.caption("Fonte: Banco Central do Brasil - IF.data (Relatorio 1 - Todas as Cooperativas)")
