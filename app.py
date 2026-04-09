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



# 1. Configuração da Página
st.set_page_config(page_title="Dashboard ENEM 2024 - Avançado", layout="wide")

# 2. Estilo CSS
st.markdown("""
<style>
    .caixa-azul {
        background-color: #26466D; padding: 25px; border-radius: 10px; color: white;
        text-align: center; margin-bottom: 20px;
    }
    .stMetric {
        background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #26466D;
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
df = df[df['sg_uf_esc'] != '  ']

def gerar_tabela_frequencia(df_input):
    freq = df_input['sg_uf_prova'].value_counts().reset_index()
    freq.columns = ['Estado', 'Freq. Absoluta']
    total = freq['Freq. Absoluta'].sum()
    freq['Freq. Relativa (%)'] = (freq['Freq. Absoluta'] / total) * 100
    freq = freq.sort_values(by='Freq. Absoluta', ascending=False)
    freq['Freq. Acum. Relativa (%)'] = freq['Freq. Relativa (%)'].cumsum()
    top_5 = freq.head(5)
    bottom_5 = freq.tail(5)
    return pd.concat([top_5, bottom_5])

# ==========================================
# 4. BARRA LATERAL (FILTROS GERAIS)
# ==========================================
st.sidebar.image("https://www.gov.br/inep/pt-br/assuntos/provas-e-exames/enem/logo_enem.png", width=150)
st.sidebar.title("Filtros Globais")

# Filtro 1: Região
regioes = sorted(df['regiao_nome_prova'].unique().tolist())
regiao_sel = st.sidebar.multiselect("1. Região do Brasil:", regioes, default=regioes)

# Filtro 2: Estado (Fica dinâmico dependendo da região escolhida)
ufs_filtradas = sorted(df[df['regiao_nome_prova'].isin(regiao_sel)]['sg_uf_prova'].dropna().unique().tolist())
uf_selecionada = st.sidebar.multiselect("2. Estados (UF):", ufs_filtradas, default=ufs_filtradas)

# Filtro 3: Dependência Administrativa da Escola
deps = sorted(df['tp_dependencia_adm_esc'].unique().tolist())
dep_sel = st.sidebar.multiselect("3. Tipo de Escola:", deps, default=deps)

# Filtro 4 e 5: Faixa por NOTAS
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Filtro de Desempenho")

# Dicionário para deixar os nomes amigáveis no menu
dicionario_notas = {
    "Média Geral (5 Notas)": "nota_media_5_notas",
    "Matemática": "nota_mt_matematica",
    "Ciências da Natureza": "nota_cn_ciencias_da_natureza",
    "Ciências Humanas": "nota_ch_ciencias_humanas",
    "Linguagens": "nota_lc_linguagens_e_codigos",
    "Redação": "nota_redacao"
}

materia_filtro = st.sidebar.selectbox("4. Filtrar notas baseado em:", list(dicionario_notas.keys()))
coluna_filtro = dicionario_notas[materia_filtro]

# O slider (barra deslizante) permite escolher o mínimo e máximo de qualquer matéria
nota_min, nota_max = st.sidebar.slider(
    f"5. Faixa de Notas em {materia_filtro}:", 
    min_value=0.0, max_value=1000.0, 
    value=(0.0, 1000.0), step=10.0
)

# ----------------------------------------------------
# PASSO 2: APLICAR TODOS OS FILTROS NO DATAFRAME
# ----------------------------------------------------

# Agora que todas as variáveis já existem, podemos filtrar!
df_filtrado_global = df[
    (df['regiao_nome_prova'].isin(regiao_sel)) &
    (df['sg_uf_prova'].isin(uf_selecionada)) &
    (df['tp_dependencia_adm_esc'].isin(dep_sel)) &
    (df[coluna_filtro] >= nota_min) &
    (df[coluna_filtro] <= nota_max)
]


# ==========================================
# 5. CABEÇALHO
# ==========================================
st.markdown("""
<div class="caixa-azul">
    <h1>Análise Estatística ENEM 2024</h1>
    <p>Explore o desempenho detalhado por áreas, distribuições de frequência e correlações.</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 6. DEFINIÇÃO DAS ABAS
# ==========================================
tab_geral, tab_exatas, tab_humanas = st.tabs(["🏠 Geral", "📐 Exatas", "📚 Humanas"])

# --- ABA GERAL ---
with tab_geral:
    st.header("Visão Macro e Indicadores")
    
    # 1. KPIs no topo da aba geral
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total de Alunos (Filtro)", f"{len(df_filtrado_global):,}".replace(',', '.'))
    kpi2.metric("Média Geral Nacional", f"{df_filtrado_global['nota_media_5_notas'].mean():.1f}")
    kpi3.metric("Maior Média Registrada", f"{df_filtrado_global['nota_media_5_notas'].max():.1f}")
    
    st.markdown("---")
    
    # 2. Divisão da tela: Gráfico de Barras e Tabela de Frequência
    col_geral_1, col_geral_2 = st.columns([2, 1])
    
    with col_geral_1:
        st.subheader("Média por Tipo de Escola")
        media_escola = df_filtrado_global.groupby('tp_dependencia_adm_esc')['nota_media_5_notas'].mean().reset_index()
        fig_escola = px.bar(media_escola, x='tp_dependencia_adm_esc', y='nota_media_5_notas', 
                            color_discrete_sequence=['#26466D'], text_auto='.1f',
                            labels={'tp_dependencia_adm_esc': 'Tipo de Escola', 'nota_media_5_notas': 'Nota Média'})
        st.plotly_chart(fig_escola, use_container_width=True)

    with col_geral_2:
        st.subheader("Frequência por Estado (Top/Bottom 5)")
        # Agora a tabela mora aqui!
        if len(df_filtrado_global) > 0:
            st.dataframe(gerar_tabela_frequencia(df_filtrado_global), hide_index=True)
        else:
            st.warning("Sem dados para a tabela.")

    st.markdown("---")
    
    # 3. Scatter Plot (Comparação de Matérias)
    st.subheader("Comparação de Desempenho entre Matérias")
    col_x, col_y = st.columns(2)
    with col_x:
        mat_x = st.selectbox("Eixo X:", ['nota_mt_matematica', 'nota_cn_ciencias_da_natureza', 'nota_ch_ciencias_humanas', 'nota_lc_linguagens_e_codigos', 'nota_redacao'], index=0)
    with col_y:
        mat_y = st.selectbox("Eixo Y:", ['nota_mt_matematica', 'nota_cn_ciencias_da_natureza', 'nota_ch_ciencias_humanas', 'nota_lc_linguagens_e_codigos', 'nota_redacao'], index=1)
    
    fig_scatter = px.scatter(df_filtrado_global.sample(min(2000, len(df_filtrado_global))), 
                             x=mat_x, y=mat_y, opacity=0.5, color_discrete_sequence=['#D9383A'])
    st.plotly_chart(fig_scatter, use_container_width=True, key="scatter_geral")
    st.caption("Amostra de 2000 registros para otimizar a visualização.")

# --- ABA EXATAS ---
with tab_exatas:
    st.header("Análise de Ciências da Natureza e Matemática")
    materia_exatas = st.radio("Selecione a matéria para detalhamento:", 
                               ["Matemática", "Ciências da Natureza"], horizontal=True)
    
    col_map = {"Matemática": "nota_mt_matematica", "Ciências da Natureza": "nota_cn_ciencias_da_natureza"}
    col_alvo = col_map[materia_exatas]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Destaques: Maior Nota", f"{df_filtrado_global[col_alvo].max():.1f}")
    c2.metric("Destaques: Menor Nota", f"{df_filtrado_global[col_alvo].min():.1f}")
    c3.metric("Destaques: Média", f"{df_filtrado_global[col_alvo].mean():.1f}")
    
    st.subheader(f"Distribuição de Notas: {materia_exatas}")
    # O histograma agora ocupa a tela toda, já que tiramos a tabela daqui
    fig_hist = px.histogram(df_filtrado_global, x=col_alvo, nbins=40, color_discrete_sequence=['#26466D'])
    st.plotly_chart(fig_hist, use_container_width=True, key="hist_exatas")
    st.info(f"**Explicação do Gráfico:** Este histograma mostra como as notas de {materia_exatas} estão distribuídas. "
            "Picos à direita indicam uma prova onde muitos alunos foram bem, enquanto picos à esquerda indicam maior dificuldade.")

# --- ABA HUMANAS ---
with tab_humanas:
    st.header("Análise de Humanas, Linguagens e Redação")
    materia_humanas = st.radio("Selecione a matéria para detalhamento:", 
                                ["Humanas", "Linguagens", "Redação"], horizontal=True)
    
    col_map_h = {"Humanas": "nota_ch_ciencias_humanas", "Linguagens": "nota_lc_linguagens_e_codigos", "Redação": "nota_redacao"}
    col_alvo_h = col_map_h[materia_humanas]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Destaques: Maior Nota", f"{df_filtrado_global[col_alvo_h].max():.1f}")
    c2.metric("Destaques: Menor Nota", f"{df_filtrado_global[col_alvo_h].min():.1f}")
    c3.metric("Destaques: Média", f"{df_filtrado_global[col_alvo_h].mean():.1f}")

    st.subheader(f"Distribuição de Notas: {materia_humanas}")
    # O histograma ocupando a tela toda também
    fig_hist_h = px.histogram(df_filtrado_global, x=col_alvo_h, nbins=40, color_discrete_sequence=['#D9383A'])
    st.plotly_chart(fig_hist_h, use_container_width=True, key="hist_humanas")
    st.info(f"**Explicação do Gráfico:** A distribuição de {materia_humanas} permite identificar a consistência dos candidatos. Em Redação, é comum observarmos concentrações em valores múltiplos de 40 ou 50 devido aos critérios de correção.")
