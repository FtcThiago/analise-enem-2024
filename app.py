import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from sqlalchemy import create_engine


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

# 1. Configuração da Página (Sempre a primeira linha)
st.set_page_config(page_title="Dashboard ENEM 2024", layout="wide", initial_sidebar_state="expanded")

# 2. Estilização Personalizada (CSS para criar o Banner Azul da imagem)
st.markdown("""
<style>
    .caixa-azul {
        background-color: #26466D; /* Azul escuro igual ao da imagem */
        padding: 30px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .caixa-azul h1 {
        color: white;
        font-size: 2.5em;
        margin-bottom: 10px;
    }
    .caixa-azul p {
        font-size: 1.1em;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

# 3. Carregamento dos Dados
@st.cache_data
def carregar_dados():
    # 3. Carregar a tabela do ENEM 2024
    query_enem = "SELECT * FROM ed_enem_2024_resultados_amos_per"
    df = pd.read_sql(query_enem, engine)
    return df

df = carregar_dados()

# ==========================================
# 4. BARRA LATERAL (SIDEBAR) - Filtros
# ==========================================
st.sidebar.markdown("### 🎓 Filtro de Notas")
nota_min = float(df['nota_media_5_notas'].min(skipna=True))
nota_max = float(df['nota_media_5_notas'].max(skipna=True))

faixa_nota = st.sidebar.slider(
    "Filtrar candidatos pela nota média:",
    min_value=nota_min,
    max_value=nota_max,
    value=(nota_min, nota_max)
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📍 Filtros Geográficos")

ufs = df['sg_uf_prova'].dropna().unique().tolist()
uf_selecionada = st.sidebar.multiselect(
    "Selecione os Estados (UF):", 
    options=ufs, 
    default=ufs[:5] # Puxando apenas os 5 primeiros por padrão
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🏫 Filtros Escolares")

deps = df['tp_dependencia_adm_esc'].dropna().unique().tolist()
dep_selecionada = st.sidebar.multiselect(
    "Dependência Administrativa:", 
    options=deps, 
    default=deps
)

# Aplicando os filtros no banco de dados
df_filtrado = df[
    (df['nota_media_5_notas'] >= faixa_nota[0]) &
    (df['nota_media_5_notas'] <= faixa_nota[1]) &
    (df['sg_uf_prova'].isin(uf_selecionada))
]

if dep_selecionada:
    df_filtrado = df_filtrado[df_filtrado['tp_dependencia_adm_esc'].isin(dep_selecionada)]

# ==========================================
# 5. ÁREA PRINCIPAL (CABEÇALHO)
# ==========================================
# Desenhando a caixa azul baseada na sua imagem
st.markdown("""
<div class="caixa-azul">
    <h1>📊 Análise de Desempenho - ENEM 2024</h1>
    <p>Plataforma de visualização e análise de dados educacionais dos candidatos do ENEM. O sistema oferece insights abrangentes sobre o desempenho dos alunos nas diferentes áreas de conhecimento, perfis regionais e infraestrutura escolar, contribuindo para o entendimento do cenário educacional brasileiro.</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 6. ABAS DE NAVEGAÇÃO (TABS) E GRÁFICOS
# ==========================================
# Criando as abas iguazinhas as da imagem (Docentes, Redes...)
aba1, aba2, aba3 = st.tabs(["📚 Visão Geral", "📝 Desempenho por Área", "🌍 Mapa de Provas"])

total_alunos = df_filtrado.shape[0]

with aba1:
    # Dividindo a tela em duas colunas para o Gráfico de Rosca e o de Barras
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Distribuição por Dependência Escolar")
        # Preparando os dados para o gráfico de rosca (Donut)
        dados_escola = df_filtrado['tp_dependencia_adm_esc'].value_counts().reset_index()
        dados_escola.columns = ['Dependência', 'Quantidade']
        
        # Gráfico de Rosca (Pie chart com furo no meio)
        fig_rosca = px.pie(
            dados_escola, 
            values='Quantidade', 
            names='Dependência', 
            hole=0.65, # Esse valor define o tamanho do buraco no meio
            color_discrete_sequence=['#26466D', '#D9383A', '#45B69C', '#F4A261']
        )
        
        # Colocando o número total bem no centro do gráfico (igual na sua imagem)
        fig_rosca.update_layout(
            annotations=[dict(text=f"<b>{total_alunos}</b><br>Alunos", x=0.5, y=0.5, font_size=20, showarrow=False)]
        )
        st.plotly_chart(fig_rosca, use_container_width=True)

    with col2:
        st.markdown("#### Média Geral por Região do Brasil")
        # Gráfico de barras vermelhas como o da imagem
        media_regiao = df_filtrado.groupby('regiao_nome_prova')['nota_media_5_notas'].mean().reset_index()
        media_regiao = media_regiao.sort_values(by='nota_media_5_notas', ascending=False)
        
        fig_barras = px.bar(
            media_regiao, 
            x='regiao_nome_prova', 
            y='nota_media_5_notas',
            color_discrete_sequence=['#D9383A'], # Cor vermelha puxada da sua imagem
            labels={'regiao_nome_prova': 'Região', 'nota_media_5_notas': 'Nota Média'},
            text_auto='.1f'
        )
        fig_barras.update_layout(xaxis_title="", yaxis_title="Média das Notas")
        st.plotly_chart(fig_barras, use_container_width=True)

with aba2:
    st.markdown("#### Desempenho Detalhado por Área de Conhecimento")
    # Tabela com as médias das matérias
    cols_notas = ['nota_cn_ciencias_da_natureza', 'nota_ch_ciencias_humanas', 
                  'nota_lc_linguagens_e_codigos', 'nota_mt_matematica', 'nota_redacao']
    medias = df_filtrado[cols_notas].mean().reset_index()
    medias.columns = ['Área de Conhecimento', 'Média de Pontos']
    medias['Área de Conhecimento'] = medias['Área de Conhecimento'].str.replace('nota_', '').str.replace('_', ' ').str.title()
    
    fig_barras_materias = px.bar(
        medias, 
        x='Área de Conhecimento', 
        y='Média de Pontos', 
        color='Área de Conhecimento',
        text_auto='.1f'
    )
    st.plotly_chart(fig_barras_materias, use_container_width=True)

with aba3:
    st.markdown("#### Densidade e Médias por Município de Prova")
    # Mapa geográfico simples e leve
    df_mapa = df_filtrado.groupby(['no_municipio_prova', 'latitude', 'longitude'])['nota_media_5_notas'].mean().reset_index()

    fig_mapa = px.scatter_mapbox(
        df_mapa, 
        lat="latitude", 
        lon="longitude", 
        color="nota_media_5_notas",
        size="nota_media_5_notas",
        hover_name="no_municipio_prova",
        color_continuous_scale="Reds",
        size_max=15, 
        zoom=3.5,
        mapbox_style="carto-positron"
    )
    fig_mapa.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_mapa, use_container_width=True)
