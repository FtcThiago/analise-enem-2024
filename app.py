import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from sqlalchemy import create_engine

# ==========================================
# 1. CONEXÃO COM BANCO DE DADOS
# ==========================================
# Pegando as chaves escondidas lá no secrets.toml
user = st.secrets["banco_enem"]["usuario"]
password = st.secrets["banco_enem"]["senha"]
host = st.secrets["banco_enem"]["host"]
porta = st.secrets["banco_enem"]["porta"]
db = st.secrets["banco_enem"]["nome_db"]

conn_string = f'postgresql://{user}:{password}@{host}/{db}'
engine = create_engine(conn_string)

# Verificar tabelas
tab_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
tabelas = pd.read_sql(tab_query, engine)

# ==========================================
# 2. CONFIGURAÇÃO DA PÁGINA E CSS
# ==========================================
st.set_page_config(page_title="Dashboard ENEM 2024 - Avançado", layout="wide")

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

# ==========================================
# 3. CARREGAMENTO DOS DADOS E FUNÇÕES
# ==========================================
@st.cache_data
def carregar_dados():
    query_enem = "SELECT * FROM ed_enem_2024_resultados_amos_per"
    df = pd.read_sql(query_enem, engine)
    
    # Tratamento numérico para as notas para evitar erros no slider
    cols_notas = [
        'nota_media_5_notas', 'nota_mt_matematica', 'nota_cn_ciencias_da_natureza',
        'nota_ch_ciencias_humanas', 'nota_lc_linguagens_e_codigos', 'nota_redacao'
    ]
    for col in cols_notas:
        if col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
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
    # Retorna a tabela completa agora para podermos dividir na aba de Estados
    return freq

# ==========================================
# 4. BARRA LATERAL (FILTROS GERAIS)
# ==========================================
st.sidebar.image("https://www.gov.br/inep/pt-br/assuntos/provas-e-exames/enem/logo_enem.png", width=150)
st.sidebar.title("Filtros Globais")

st.sidebar.markdown("### 🎯 Filtro de Desempenho")

dicionario_notas = {
    "Média Geral (5 Notas)": "nota_media_5_notas",
    "Matemática": "nota_mt_matematica",
    "Ciências da Natureza": "nota_cn_ciencias_da_natureza",
    "Ciências Humanas": "nota_ch_ciencias_humanas",
    "Linguagens": "nota_lc_linguagens_e_codigos",
    "Redação": "nota_redacao"
}

materia_filtro = st.sidebar.selectbox("1. Filtrar notas baseado em:", list(dicionario_notas.keys()))
coluna_filtro = dicionario_notas[materia_filtro]

nota_min, nota_max = st.sidebar.slider(
    f"2. Faixa de Notas em {materia_filtro}:", 
    min_value=0.0, max_value=1000.0, 
    value=(0.0, 1000.0), step=10.0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📍 Filtros Locais e Escola")

regioes = sorted(df['regiao_nome_prova'].unique().tolist())
regiao_sel = st.sidebar.multiselect("1. Região do Brasil:", regioes, default=regioes)

ufs_filtradas = sorted(df[df['regiao_nome_prova'].isin(regiao_sel)]['sg_uf_prova'].dropna().unique().tolist())
uf_selecionada = st.sidebar.multiselect("2. Estados (UF):", ufs_filtradas, default=ufs_filtradas)

deps = sorted(df['tp_dependencia_adm_esc'].unique().tolist())
dep_sel = st.sidebar.multiselect("3. Tipo de Escola:", deps, default=deps)

# Aplicando todos os filtros
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
# Nova aba de Estados adicionada aqui
tab_geral, tab_exatas, tab_humanas, tab_estados = st.tabs(["🏠 Geral", "📐 Exatas", "📚 Humanas", "🗺️ Estados"])

# --- ABA GERAL ---
with tab_geral:
    st.header("Visão Macro e Indicadores")
    
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total de Alunos (Filtro)", f"{len(df_filtrado_global):,}".replace(',', '.'))
    if len(df_filtrado_global) > 0:
        kpi2.metric("Média Geral Nacional", f"{df_filtrado_global['nota_media_5_notas'].mean():.1f}")
        kpi3.metric("Maior Média Registrada", f"{df_filtrado_global['nota_media_5_notas'].max():.1f}")
    else:
        kpi2.metric("Média Geral Nacional", "N/A")
        kpi3.metric("Maior Média Registrada", "N/A")
    
    st.markdown("---")
    
    # O gráfico agora ocupa a tela toda (tabela foi para a nova aba)
    st.subheader("Média por Tipo de Escola")
    if len(df_filtrado_global) > 0:
        media_escola = df_filtrado_global.groupby('tp_dependencia_adm_esc')['nota_media_5_notas'].mean().reset_index()
        fig_escola = px.bar(media_escola, x='tp_dependencia_adm_esc', y='nota_media_5_notas', 
                            color_discrete_sequence=['#26466D'], text_auto='.1f',
                            labels={'tp_dependencia_adm_esc': 'Tipo de Escola', 'nota_media_5_notas': 'Nota Média'})
        st.plotly_chart(fig_escola, use_container_width=True)
    else:
        st.warning("Sem dados para exibir o gráfico.")

    st.markdown("---")
    
    st.subheader("Comparação de Desempenho entre Matérias")
    col_x, col_y = st.columns(2)
    with col_x:
        mat_x = st.selectbox("Eixo X:", ['nota_mt_matematica', 'nota_cn_ciencias_da_natureza', 'nota_ch_ciencias_humanas', 'nota_lc_linguagens_e_codigos', 'nota_redacao'], index=0)
    with col_y:
        mat_y = st.selectbox("Eixo Y:", ['nota_mt_matematica', 'nota_cn_ciencias_da_natureza', 'nota_ch_ciencias_humanas', 'nota_lc_linguagens_e_codigos', 'nota_redacao'], index=1)
    
    if len(df_filtrado_global) > 0:
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
    
    if len(df_filtrado_global) > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("Destaques: Maior Nota", f"{df_filtrado_global[col_alvo].max():.1f}")
        c2.metric("Destaques: Menor Nota", f"{df_filtrado_global[col_alvo].min():.1f}")
        c3.metric("Destaques: Média", f"{df_filtrado_global[col_alvo].mean():.1f}")
        
        st.subheader(f"Distribuição de Notas: {materia_exatas}")
        fig_hist = px.histogram(df_filtrado_global, x=col_alvo, nbins=40, color_discrete_sequence=['#26466D'])
        st.plotly_chart(fig_hist, use_container_width=True, key="hist_exatas")
        st.info(f"**Explicação do Gráfico:** Este histograma mostra como as notas de {materia_exatas} estão distribuídas. "
                "Picos à direita indicam uma prova onde muitos alunos foram bem, enquanto picos à esquerda indicam maior dificuldade.")
    else:
        st.warning("Sem dados com os filtros atuais.")

# --- ABA HUMANAS ---
with tab_humanas:
    st.header("Análise de Humanas, Linguagens e Redação")
    materia_humanas = st.radio("Selecione a matéria para detalhamento:", 
                                ["Humanas", "Linguagens", "Redação"], horizontal=True)
    
    col_map_h = {"Humanas": "nota_ch_ciencias_humanas", "Linguagens": "nota_lc_linguagens_e_codigos", "Redação": "nota_redacao"}
    col_alvo_h = col_map_h[materia_humanas]
    
    if len(df_filtrado_global) > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("Destaques: Maior Nota", f"{df_filtrado_global[col_alvo_h].max():.1f}")
        c2.metric("Destaques: Menor Nota", f"{df_filtrado_global[col_alvo_h].min():.1f}")
        c3.metric("Destaques: Média", f"{df_filtrado_global[col_alvo_h].mean():.1f}")

        st.subheader(f"Distribuição de Notas: {materia_humanas}")
        fig_hist_h = px.histogram(df_filtrado_global, x=col_alvo_h, nbins=40, color_discrete_sequence=['#D9383A'])
        st.plotly_chart(fig_hist_h, use_container_width=True, key="hist_humanas")
        st.info(f"**Explicação do Gráfico:** A distribuição de {materia_humanas} permite identificar a consistência dos candidatos. Em Redação, é comum observarmos concentrações em valores múltiplos de 40 ou 50 devido aos critérios de correção.")
    else:
        st.warning("Sem dados com os filtros atuais.")

# --- ABA ESTADOS (NOVA) ---
with tab_estados:
    st.header("Análise Geográfica e Desempenho Regional")
    
    if len(df_filtrado_global) > 0:
        # Gera a tabela completa para dividir nas colunas
        tabela_frequencia_completa = gerar_tabela_frequencia(df_filtrado_global)
        
        col_top, col_bottom = st.columns(2)
        
        with col_top:
            st.subheader("Top 5 - Estados com Mais Alunos")
            st.dataframe(tabela_frequencia_completa.head(5), hide_index=True)
            
        with col_bottom:
            st.subheader("Bottom 5 - Estados com Menos Alunos")
            st.dataframe(tabela_frequencia_completa.tail(5), hide_index=True)
            
        st.markdown("---")
        
        # Filtro interno para o gráfico de Regiões
        st.subheader("Desempenho Acima da Média por Região")
        materia_estado = st.selectbox("Selecione a matéria para analisar os destaques regionais:", 
                                      list(dicionario_notas.keys()), key="filtro_estado")
        col_estado_alvo = dicionario_notas[materia_estado]
        
        # Calcula a média da matéria escolhida baseada nos filtros atuais
        media_atual = df_filtrado_global[col_estado_alvo].mean()
        st.info(f"A média atual de **{materia_estado}** (considerando os filtros globais) é de **{media_atual:.1f}** pontos.")
        
        # Filtra quem está acima da média e agrupa por região
        df_acima_media = df_filtrado_global[df_filtrado_global[col_estado_alvo] > media_atual]
        
        if len(df_acima_media) > 0:
            contagem_regiao = df_acima_media['regiao_nome_prova'].value_counts().reset_index()
            contagem_regiao.columns = ['Região', 'Quantidade de Alunos']
            
            fig_regioes = px.bar(contagem_regiao, x='Região', y='Quantidade de Alunos', 
                                 text_auto=True, color='Região', 
                                 title=f"Qtd. de Alunos acima da média em {materia_estado}")
            st.plotly_chart(fig_regioes, use_container_width=True, key="bar_regioes")
        else:
            st.warning("Nenhum aluno atingiu notas acima da média com a configuração atual.")
            
    else:
        st.warning("Sem dados para a análise estadual. Ajuste os filtros globais.")
