import streamlit as st
import pandas as pd
import plotly.express as px
from services.conexao_sheets import carregar_dados

# ==============================================================================
# 0. PROTEÇÃO DE ACESSO (SEMPRE A PRIMEIRA COISA)
# ==============================================================================
if "logado" not in st.session_state or not st.session_state["logado"]:
    st.switch_page("app.py")

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Estoque por Destino", page_icon="📦", layout="wide")

# ==============================================================================
# 2. CSS (CORRIGE A SIDEBAR E O LAYOUT)
# ==============================================================================
st.markdown("""
<style>
    /* Esconde a Nav Nativa do Streamlit para usar a nossa */
    [data-testid="stSidebarNav"] {display: none;}
    
    /* Ajuste de metricas */
    [data-testid="stMetricValue"] {
        font-size: 26px;
        color: #00B17C;
    }
    div[data-testid="stMetricLabel"] {
        font-weight: bold;
    }
    
    /* Ajuste da Sidebar Personalizada */
    section[data-testid="stSidebar"] > div {
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding-top: 0px !important;
        padding-bottom: 20px !important;
    }
    div[data-testid="stSidebarUserContent"] {
        padding-top: 2rem !important;
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    div[data-testid="stImage"] { margin-bottom: 20px; }
    .footer-container { margin-top: auto; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. SIDEBAR (MENU LATERAL)
# ==============================================================================
with st.sidebar:
    try:
        st.image("assets/logo.png", use_container_width=True)
    except:
        st.header("MAROSO")

    st.write("") 
    st.caption("MENU PRINCIPAL")
    st.page_link("pages/1_📊_Dashboard.py", label="Dashboard", icon="📊") 
    st.page_link("pages/2_🚛_Processo_Devolucao.py", label="Novo Processo", icon="🚛")
    st.page_link("pages/3_📋_Gestao_Tratativas.py", label="Gestão Tratativas", icon="📋")
    st.page_link("pages/4_📍_Posições.py", label="Posições & Rotas", icon="📍")
    st.page_link("pages/5_📦_Estoque_Destino.py", label="Estoque Destino", icon = "📦") 

    st.markdown('<div class="footer-container">', unsafe_allow_html=True)
    st.markdown("---")
    
    c_perfil, c_texto = st.columns([0.25, 0.75])
    with c_perfil:
        st.markdown("""<div style='font-size: 24px; text-align: center; background: var(--secondary-background-color); border-radius: 50%; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; border: 1px solid #444;'>👤</div>""", unsafe_allow_html=True)
    with c_texto:
        usuario_nome = st.session_state.get('usuario', 'Admin').split(' ')[0].title()
        st.markdown(f"""<div style='line-height: 1.2;'><span style='font-weight: bold; font-size: 14px;'>{usuario_nome}</span><br><span style='font-size: 11px; opacity: 0.7;'>Maroso Transporte</span></div>""", unsafe_allow_html=True)

    st.write("")
    if st.button("Sair", use_container_width=True):
        st.session_state["logado"] = False
        st.switch_page("app.py")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 4. FUNÇÕES UTILITÁRIAS
# ==============================================================================
def converter_float(valor):
    """Garante que R$ 1.000,00 vire 1000.00 float puro"""
    if pd.isna(valor) or valor == "": return 0.0
    if isinstance(valor, (float, int)): return float(valor)
    
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v[-3:]: 
        v = v.replace(".", "").replace(",", ".")
    elif "." in v[-3:]:
        v = v.replace(",", "")
    
    try:
        return float(v)
    except:
        return 0.0

def carregar_dados_consolidados():
    """
    Faz o JOIN entre Processos (Capa) e Itens (Detalhe)
    """
    with st.spinner("Cruzando dados de Processos e Itens..."):
        # 1. Carrega as duas tabelas
        df_processos = carregar_dados("REGISTRO_DEVOLUCOES")
        
        # --- CORREÇÃO DO ERRO DO DEBUG ---
        # O nome correto no TAB_IDS é 'REGISTRO_ITENS', não 'ITENS_DEVOLUCAO'
        df_itens = carregar_dados("REGISTRO_ITENS") 
        # ---------------------------------

        if df_processos.empty or df_itens.empty:
            return pd.DataFrame()

        # 2. Garante que as chaves de ligação sejam strings limpas
        col_id_proc = "ID_PROCESSO" # PK Processo
        col_id_item = "ID_PROCESSO" # FK Item
        
        # Se na tabela de itens o nome da coluna for diferente (ex: "ID_PAI"), ajuste aqui
        if col_id_item not in df_itens.columns:
            # Tenta achar a coluna certa se não for ID_PROCESSO
            possiveis = [c for c in df_itens.columns if "ID" in c and "PROC" in c]
            if possiveis: col_id_item = possiveis[0]
        
        df_processos[col_id_proc] = df_processos[col_id_proc].astype(str).str.strip()
        df_itens[col_id_item] = df_itens[col_id_item].astype(str).str.strip()

        # 3. Tratamento Numérico nos Itens
        if "VALOR_TOTAL" in df_itens.columns:
            df_itens["VALOR_TOTAL_FLOAT"] = df_itens["VALOR_TOTAL"].apply(converter_float)
        else:
            df_itens["VALOR_TOTAL_FLOAT"] = 0.0
            
        if "QTD" in df_itens.columns:
            df_itens["QTD_FLOAT"] = df_itens["QTD"].apply(converter_float)
        else:
             df_itens["QTD_FLOAT"] = 0.0

        # 4. O JOIN MÁGICO (Merge)
        cols_capa = [col_id_proc, "LOCAL_DESTINO", "NF", "VEICULO", "DATA_EMISSAO"]
        cols_existentes = [c for c in cols_capa if c in df_processos.columns]
        
        df_completo = pd.merge(
            df_itens, 
            df_processos[cols_existentes], 
            left_on=col_id_item, 
            right_on=col_id_proc, 
            how="inner"
        )
        
        return df_completo

# ==============================================================================
# 5. INTERFACE PRINCIPAL
# ==============================================================================
st.title("📦 Controle de Estoque por Destino")
st.markdown("Visão consolidada de produtos aguardando movimentação ou tratativa.")

# Tenta carregar. Se der erro de Plotly, avisa o usuário.
try:
    df = carregar_dados_consolidados()
except ImportError:
    st.error("⚠️ Erro de Biblioteca: O 'plotly' não está instalado. Pare o terminal e rode: pip install plotly")
    st.stop()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

if df.empty:
    st.warning("📭 Nenhum dado encontrado ou erro na conexão das tabelas.")
else:
    # --- FILTROS LATERAIS ---
    with st.sidebar:
        st.header("Filtros")
        
        if "LOCAL_DESTINO" in df.columns:
            locais_disponiveis = df["LOCAL_DESTINO"].dropna().unique().tolist()
            locais_disponiveis = sorted([l for l in locais_disponiveis if str(l).strip() != ""])
        else:
            locais_disponiveis = []
        
        local_selecionado = st.selectbox(
            "📍 Selecione o Destino", 
            ["Todos"] + locais_disponiveis
        )
        
        nf_filtro = st.text_input("Filtrar por NF")

    # --- APLICAÇÃO DOS FILTROS ---
    df_filtrado = df.copy()
    
    if local_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["LOCAL_DESTINO"] == local_selecionado]
        
    if nf_filtro:
        df_filtrado = df_filtrado[df_filtrado["NF"].astype(str).str.contains(nf_filtro, na=False)]

    # --- KPIS ---
    col1, col2, col3 = st.columns(3)
    
    qtd_total = df_filtrado["QTD_FLOAT"].sum()
    valor_total = df_filtrado["VALOR_TOTAL_FLOAT"].sum()
    processos_unicos = df_filtrado["ID_PROCESSO"].nunique()
    
    col1.metric("📦 Volume Total (Qtd)", f"{int(qtd_total)}")
    col2.metric("💰 Valor em Mercadoria", f"R$ {valor_total:,.2f}")
    col3.metric("🚛 Processos/NFs Envolvidos", f"{processos_unicos}")
    
    st.divider()

    # --- GRÁFICO E TABELA ---
    c_graf, c_tab = st.columns([1, 1.5])
    
    with c_graf:
        st.subheader("🔥 Tier List: Itens de Maior Valor")
        
        if not df_filtrado.empty:
            df_tier = df_filtrado.groupby(["DESCRICAO", "NF"])["VALOR_TOTAL_FLOAT"].sum().reset_index()
            df_tier = df_tier.sort_values(by="VALOR_TOTAL_FLOAT", ascending=False).head(10)
            
            fig = px.bar(
                df_tier, 
                x="VALOR_TOTAL_FLOAT", 
                y="DESCRICAO", 
                orientation='h',
                text_auto='.2s',
                color="VALOR_TOTAL_FLOAT",
                color_continuous_scale="Reds",
                hover_data=["NF"],
                title="Top 10 Itens (Valor R$)"
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para o gráfico.")

    with c_tab:
        st.subheader("📋 Detalhamento dos Itens")
        cols_view = ["ID_PROCESSO", "NF", "COD_ITEM", "DESCRICAO", "QTD", "VALOR_TOTAL", "LOCAL_DESTINO"]
        cols_final = [c for c in cols_view if c in df_filtrado.columns]
        
        st.dataframe(
            df_filtrado[cols_final], 
            use_container_width=True, 
            hide_index=True,
            height=400
        )