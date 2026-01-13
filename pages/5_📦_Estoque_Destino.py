import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from services.conexao_sheets import carregar_dados

# ==============================================================================
# 0. PROTEÇÃO DE ACESSO
# ==============================================================================
if "logado" not in st.session_state or not st.session_state["logado"]:
    st.switch_page("app.py")

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Estoque por Destino", page_icon="📦", layout="wide")

# CSS Personalizado
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 26px; color: #00B17C;
    }
    div[data-testid="stMetricLabel"] { font-weight: bold; }
    
    /* Container de Filtros */
    .stExpander {
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 8px;
        background-color: #1E1E1E; /* Ajuste conforme seu tema */
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] > div {
        height: 100vh; display: flex; flex-direction: column; justify-content: space-between;
        padding-top: 0px !important; padding-bottom: 20px !important;
    }
    div[data-testid="stSidebarUserContent"] {
        padding-top: 2rem !important; display: flex; flex-direction: column; height: 100%;
    }
    div[data-testid="stImage"] { margin-bottom: 20px; }
    .footer-container { margin-top: auto; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. SIDEBAR
# ==============================================================================
with st.sidebar:
    try: st.image("assets/logo.png", use_container_width=True)
    except: st.header("MAROSO")

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
# 3. FUNÇÕES DE CARGA E TRATAMENTO
# ==============================================================================
def converter_float(valor):
    if pd.isna(valor) or valor == "": return 0.0
    if isinstance(valor, (float, int)): return float(valor)
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v[-3:]: v = v.replace(".", "").replace(",", ".")
    elif "." in v[-3:]: v = v.replace(",", "")
    try: return float(v)
    except: return 0.0

@st.cache_data(ttl=60) # Cache de 60 segundos para performance
def carregar_dados_consolidados():
    # 1. Carrega tabelas
    df_processos = carregar_dados("REGISTRO_DEVOLUCOES")
    df_itens = carregar_dados("REGISTRO_ITENS")

    if df_processos.empty or df_itens.empty: return pd.DataFrame()

    # 2. Normaliza Chaves
    col_id_proc = "ID_PROCESSO"
    col_id_item = "ID_PROCESSO"
    if col_id_item not in df_itens.columns:
        possiveis = [c for c in df_itens.columns if "ID" in c and "PROC" in c]
        if possiveis: col_id_item = possiveis[0]
    
    df_processos[col_id_proc] = df_processos[col_id_proc].astype(str).str.strip()
    df_itens[col_id_item] = df_itens[col_id_item].astype(str).str.strip()

    # 3. Tratamento Numérico
    col_val = "VALOR_TOTAL" if "VALOR_TOTAL" in df_itens.columns else "VALOR"
    df_itens["VALOR_TOTAL_FLOAT"] = df_itens[col_val].apply(converter_float) if col_val in df_itens.columns else 0.0
    df_itens["QTD_FLOAT"] = df_itens["QTD"].apply(converter_float) if "QTD" in df_itens.columns else 0.0

    # 4. Merge
    cols_capa = [col_id_proc, "LOCAL_DESTINO", "NF", "VEICULO", "DATA_EMISSAO", "STATUS"]
    cols_existentes = [c for c in cols_capa if c in df_processos.columns]
    
    df_full = pd.merge(df_itens, df_processos[cols_existentes], left_on=col_id_item, right_on=col_id_proc, how="inner")
    
    # 5. LÓGICA DE DESTINO VAZIO (DARK DATA)
    if "LOCAL_DESTINO" in df_full.columns:
        df_full["LOCAL_DESTINO"] = df_full["LOCAL_DESTINO"].fillna("Sem Destino").replace("", "Sem Destino")
    
    # 6. Tratamento de Data para Filtro
    if "DATA_EMISSAO" in df_full.columns:
        df_full["DT_OBJ"] = pd.to_datetime(df_full["DATA_EMISSAO"], dayfirst=True, errors='coerce')
    
    return df_full

# ==============================================================================
# 4. INTERFACE PRINCIPAL
# ==============================================================================
st.title("Controle de Estoque por Destino")
st.markdown("Visão consolidada de produtos aguardando movimentação ou tratativa.")

# Carga de Dados
try:
    df = carregar_dados_consolidados()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

if df.empty:
    st.warning("📭 Nenhum dado encontrado. Verifique as planilhas.")
    st.stop()

# --- ÁREA DE FILTROS & VISUALIZAÇÃO (EXPANDER) ---
with st.expander("🔍 Filtros & Visualização", expanded=True):
    f1, f2, f3 = st.columns([1.5, 1.5, 2])
    
    # A. Filtro de Data
    dt_min = df["DT_OBJ"].min().date() if not df["DT_OBJ"].isna().all() else datetime.now().date()
    dt_max = df["DT_OBJ"].max().date() if not df["DT_OBJ"].isna().all() else datetime.now().date()
    
    with f1:
        datas_sel = st.date_input("Período de Emissão", value=(dt_min, dt_max), format="DD/MM/YYYY")

    # B. Filtro de Destino (Multiselect)
    with f2:
        destinos_unicos = sorted(df["LOCAL_DESTINO"].unique())
        # Tenta selecionar "Sem Destino" por padrão se existir, pra chamar atenção
        padrao = ["Sem Destino"] if "Sem Destino" in destinos_unicos else []
        destinos_sel = st.multiselect("Locais de Destino", options=destinos_unicos, default=None, placeholder="Todos os destinos")

    # C. Busca Lambda (Global)
    with f3:
        search_term = st.text_input("Buscar Geral (NF, Item, Código, ID...)", placeholder="Digite para filtrar...")

# --- APLICAÇÃO DOS FILTROS (ENGINE) ---
df_filt = df.copy()

# 1. Filtro Data
if isinstance(datas_sel, tuple) and len(datas_sel) == 2:
    start_d, end_d = datas_sel
    # Filtra onde a data não é NaT e está no range
    mask_data = (df_filt["DT_OBJ"].dt.date >= start_d) & (df_filt["DT_OBJ"].dt.date <= end_d)
    df_filt = df_filt[mask_data]

# 2. Filtro Destino
if destinos_sel:
    df_filt = df_filt[df_filt["LOCAL_DESTINO"].isin(destinos_sel)]

# 3. Filtro Busca Lambda (O Poderoso)
if search_term:
    t = search_term.lower()
    # Cria uma máscara booleana varrendo várias colunas como string
    mask_search = (
        df_filt["DESCRICAO"].astype(str).str.lower().str.contains(t) |
        df_filt["NF"].astype(str).str.lower().str.contains(t) |
        df_filt["COD_ITEM"].astype(str).str.lower().str.contains(t) |
        df_filt["ID_PROCESSO"].astype(str).str.lower().str.contains(t) |
        df_filt["VEICULO"].astype(str).str.lower().str.contains(t)
    )
    df_filt = df_filt[mask_search]

st.divider()

# --- RESULTADOS APÓS FILTRO ---
if df_filt.empty:
    st.info("🔎 Nenhum registro encontrado com esses filtros.")
else:
    # --- KPIs ---
    k1, k2, k3, k4 = st.columns(4)
    
    qtd_total = df_filt["QTD_FLOAT"].sum()
    valor_total = df_filt["VALOR_TOTAL_FLOAT"].sum()
    nfs_unicas = df_filt["NF"].nunique()
    
    # Contagem de Itens Sem Destino (Crítico)
    sem_destino_count = len(df_filt[df_filt["LOCAL_DESTINO"] == "Sem Destino"])
    delta_dest = f"{sem_destino_count} pendentes" if sem_destino_count > 0 else "Tudo alocado"
    cor_delta = "inverse" if sem_destino_count > 0 else "off"

    k1.metric("📦 Volume (Qtd)", f"{int(qtd_total)}")
    k2.metric("💰 Valor Mercadoria", f"R$ {valor_total:,.2f}")
    k3.metric("📄 NFs Envolvidas", f"{nfs_unicas}")
    k4.metric("📍 Sem Destino", sem_destino_count, delta=delta_dest, delta_color=cor_delta)

    st.write("")
    
    # --- GRÁFICO E TABELA ---
    c_graf, c_tab = st.columns([1, 1.5])
    
    with c_graf:
        st.subheader("🔥 Top Valor em Estoque")
        
        # Agrupamento Inteligente
        df_tier = df_filt.groupby(["DESCRICAO", "LOCAL_DESTINO"])["VALOR_TOTAL_FLOAT"].sum().reset_index()
        df_tier = df_tier.sort_values(by="VALOR_TOTAL_FLOAT", ascending=False).head(10)
        
        # Gráfico dinâmico
        fig = px.bar(
            df_tier, 
            x="VALOR_TOTAL_FLOAT", 
            y="DESCRICAO", 
            orientation='h',
            text_auto='.2s',
            color="LOCAL_DESTINO", # Pinta por destino pra facilitar visualização
            title="Top 10 Itens (R$)",
            height=400
        )
        fig.update_layout(
            yaxis={'categoryorder':'total ascending'}, 
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    with c_tab:
        st.subheader(f"📋 Detalhes ({len(df_filt)} itens)")
        
        # Colunas prioritárias
        cols_view = ["ID_PROCESSO", "NF", "COD_ITEM", "DESCRICAO", "QTD", "VALOR_TOTAL", "LOCAL_DESTINO", "DATA_EMISSAO"]
        cols_final = [c for c in cols_view if c in df_filt.columns]
        
        st.dataframe(
            df_filt[cols_final], 
            use_container_width=True, 
            hide_index=True,
            height=400
        )