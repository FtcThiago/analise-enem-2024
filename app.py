#Importação das bibliotecas
import pandas as pd
from sqlalchemy import create_engine
import streamlit as st
import psycopg2
import plotly.express as px


# 1. Conexão (Troque o USER e PASSWORD pelos seus)
user = 'data_iesb'
password = 'iesb'
host = 'bigdata.dataiesb.com'
db = 'iesb'

conn_string = f'postgresql://{user}:{password}@{host}/{db}'
engine = create_engine(conn_string)

# 2. Verificar tabelas
tab_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
tabelas = pd.read_sql(tab_query, engine)
print("Tabelas no banco:", tabelas)

# 1. Configuração Inicial da Página
st.set_page_config(page_title="Análise ENEM 2024", layout="wide")
st.title("📊 Painel de Análise de Dados - ENEM 2024")
st.markdown("Análise exploratória da base de amostra do ENEM 2024 (67.487 registros).")

# 2. Carregamento dos Dados (Cache para ficar rápido)
@st.cache_data
def carregar_dados():
    # 3. Carregar a tabela do ENEM 2024
    query_enem = "SELECT * FROM ed_enem_2024_resultados_amos_per"
    df = pd.read_sql(query_enem, engine)
    return df

df = carregar_dados()

# 3. Criando a Barra Lateral (Filtros)
st.sidebar.header("Filtros de Pesquisa")

# Filtro de UF
todas_ufs = df['sg_uf_prova'].dropna().unique().tolist()
uf_selecionada = st.sidebar.multiselect(
    "Selecione as UFs:", 
    options=todas_ufs, 
    default=todas_ufs[:3] # Deixa as 3 primeiras marcadas por padrão para não pesar
)

# Filtro de Faixa de Notas (Média Geral)
nota_min = float(df['nota_media_5_notas'].min(skipna=True))
nota_max = float(df['nota_media_5_notas'].max(skipna=True))

faixa_nota = st.sidebar.slider(
    "Faixa de Nota Média:",
    min_value=nota_min,
    max_value=nota_max,
    value=(nota_min, nota_max)
)

# Filtro de Dependência Administrativa da Escola
deps = df['tp_dependencia_adm_esc'].dropna().unique().tolist()
dep_selecionada = st.sidebar.multiselect(
    "Tipo de Escola (Dependência Adm.):", 
    options=deps, 
    default=deps
)

# 4. Aplicando os Filtros no DataFrame
df_filtrado = df[
    (df['sg_uf_prova'].isin(uf_selecionada)) &
    (df['nota_media_5_notas'] >= faixa_nota[0]) &
    (df['nota_media_5_notas'] <= faixa_nota[1])
]

if dep_selecionada:
    df_filtrado = df_filtrado[df_filtrado['tp_dependencia_adm_esc'].isin(dep_selecionada)]

st.write(f"**Total de alunos filtrados:** {df_filtrado.shape[0]} de {df.shape[0]}")

# ==========================================
# 5. Visualizações de Dados com Plotly
# ==========================================

col1, col2 = st.columns(2)

# Gráfico 1: Distribuição das Notas Médias (Histograma)
with col1:
    st.subheader("Distribuição das Notas Médias")
    fig_hist = px.histogram(
        df_filtrado, 
        x="nota_media_5_notas", 
        nbins=30,
        color_discrete_sequence=["#1f77b4"],
        labels={"nota_media_5_notas": "Nota Média (5 áreas)", "count": "Quantidade de Alunos"}
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# Gráfico 2: Média por Área de Conhecimento (Gráfico de Barras)
with col2:
    st.subheader("Média de Notas por Área")
    # Calculando a média de cada coluna de nota
    cols_notas = ['nota_cn_ciencias_da_natureza', 'nota_ch_ciencias_humanas', 
                  'nota_lc_linguagens_e_codigos', 'nota_mt_matematica', 'nota_redacao']
    medias = df_filtrado[cols_notas].mean().reset_index()
    medias.columns = ['Área', 'Média']
    # Renomeando para ficar bonito no gráfico
    medias['Área'] = medias['Área'].str.replace('nota_', '').str.replace('_', ' ').str.title()
    
    fig_barras = px.bar(
        medias, 
        x='Área', 
        y='Média', 
        color='Área',
        text_auto='.2f'
    )
    st.plotly_chart(fig_barras, use_container_width=True)

# Gráfico 3: Distribuição Geográfica das Provas (Mapa)
st.subheader("Distribuição Geográfica (Média por Local de Prova)")
# Agrupando por município para não plotar dezenas de milhares de pontos no mapa de uma vez
df_mapa = df_filtrado.groupby(['no_municipio_prova', 'latitude', 'longitude'])['nota_media_5_notas'].mean().reset_index()

fig_mapa = px.scatter_mapbox(
    df_mapa, 
    lat="latitude", 
    lon="longitude", 
    color="nota_media_5_notas",
    size="nota_media_5_notas",
    hover_name="no_municipio_prova",
    color_continuous_scale=px.colors.cyclical.IceFire,
    size_max=15, 
    zoom=3,
    mapbox_style="carto-positron"
)
st.plotly_chart(fig_mapa, use_container_width=True)
