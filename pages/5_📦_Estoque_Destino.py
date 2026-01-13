import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
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

st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
    [data-testid="stMetricValue"] {font-size: 26px; color: #00B17C;}
    div[data-testid="stMetricLabel"] {font-weight: bold;}
    .stExpander {border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; background-color: #1E1E1E;}
    section[data-testid="stSidebar"] > div {height: 100vh; display: flex; flex-direction: column; justify-content: space-between; padding-top: 0px !important; padding-bottom: 20px !important;}
    div[data-testid="stSidebarUserContent"] {padding-top: 2rem !important; display: flex; flex-direction: column; height: 100%;}
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
# 3. FUNÇÕES DE SUPORTE
# ==============================================================================
def converter_float(valor):
    if pd.isna(valor) or valor == "": return 0.0
    if isinstance(valor, (float, int)): return float(valor)
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v[-3:]: v = v.replace(".", "").replace(",", ".")
    elif "." in v[-3:]: v = v.replace(",", "")
    try: return float(v)
    except: return 0.0

@st.cache_data(ttl=60)
def carregar_dados_consolidados():
    df_processos = carregar_dados("REGISTRO_DEVOLUCOES")
    df_itens = carregar_dados("REGISTRO_ITENS")

    if df_processos.empty or df_itens.empty: return pd.DataFrame()

    col_id_proc = "ID_PROCESSO"
    col_id_item = "ID_PROCESSO"
    if col_id_item not in df_itens.columns:
        possiveis = [c for c in df_itens.columns if "ID" in c and "PROC" in c]
        if possiveis: col_id_item = possiveis[0]
    
    df_processos[col_id_proc] = df_processos[col_id_proc].astype(str).str.strip()
    df_itens[col_id_item] = df_itens[col_id_item].astype(str).str.strip()

    col_val = "VALOR_TOTAL" if "VALOR_TOTAL" in df_itens.columns else "VALOR"
    df_itens["VALOR_TOTAL_FLOAT"] = df_itens[col_val].apply(converter_float) if col_val in df_itens.columns else 0.0
    df_itens["QTD_FLOAT"] = df_itens["QTD"].apply(converter_float) if "QTD" in df_itens.columns else 0.0

    # Trazemos mais dados do pai para o rastro (OC, MOTORISTA, STATUS_FISCAL)
    cols_capa = [col_id_proc, "LOCAL_DESTINO", "NF", "VEICULO", "DATA_EMISSAO", "STATUS", "OC", "MOTORISTA", "STATUS_FISCAL"]
    cols_existentes = [c for c in cols_capa if c in df_processos.columns]
    
    df_full = pd.merge(df_itens, df_processos[cols_existentes], left_on=col_id_item, right_on=col_id_proc, how="inner")
    
    if "LOCAL_DESTINO" in df_full.columns:
        df_full["LOCAL_DESTINO"] = df_full["LOCAL_DESTINO"].fillna("Sem Destino").replace("", "Sem Destino")
    
    if "DATA_EMISSAO" in df_full.columns:
        df_full["DT_OBJ"] = pd.to_datetime(df_full["DATA_EMISSAO"], dayfirst=True, errors='coerce')
    
    return df_full

# ==============================================================================
# 4. MODAL DE RASTRO (NOVIDADE)
# ==============================================================================
@st.dialog("🕵️ Rastro Detalhado do Item", width="large")
def modal_rastro(item):
    st.markdown(f"### {item.get('DESCRICAO', 'Item')}")
    st.caption(f"Cód: {item.get('COD_ITEM', '-')}")
    
    st.divider()
    
    # Linha 1: Origem
    c1, c2, c3 = st.columns(3)
    c1.metric("Processo ID", item.get('ID_PROCESSO', '-'))
    c2.metric("Nota Fiscal", item.get('NF', '-'))
    c3.metric("Ocorrência (OC)", item.get('OC', '-')) # Aqui está o que você queria!
    
    # Linha 2: Valores
    c4, c5, c6 = st.columns(3)
    val = float(item.get('VALOR_TOTAL_FLOAT', 0))
    qtd = float(item.get('QTD_FLOAT', 0))
    c4.metric("Valor Total", f"R$ {val:,.2f}")
    c5.metric("Quantidade", f"{int(qtd)}")
    c6.metric("Status Fiscal", item.get('STATUS_FISCAL', '-'))
    
    st.divider()
    st.markdown("#### 🚚 Logística de Origem")
    col_log1, col_log2, col_log3 = st.columns(3)
    col_log1.text_input("Motorista", value=item.get('MOTORISTA', '-'), disabled=True)
    col_log2.text_input("Veículo", value=item.get('VEICULO', '-'), disabled=True)
    col_log3.text_input("Destino Atual", value=item.get('LOCAL_DESTINO', '-'), disabled=True)
    
    if st.button("Fechar Detalhes", use_container_width=False):
        st.rerun()

# ==============================================================================
# 5. INTERFACE PRINCIPAL
# ==============================================================================
st.title("📦 Controle de Estoque por Destino")
st.markdown("Visão consolidada. **Clique em um item na tabela para ver o rastro completo.**")

try:
    df = carregar_dados_consolidados()
except Exception as e:
    st.error(f"Erro ao carregar: {e}")
    st.stop()

if df.empty:
    st.warning("📭 Nenhum dado encontrado.")
    st.stop()

# --- FILTROS ---
with st.expander("🔍 Filtros & Visualização", expanded=True):
    f1, f2, f3 = st.columns([1.5, 1.5, 2])
    
    dt_min = df["DT_OBJ"].min().date() if "DT_OBJ" in df and not df["DT_OBJ"].isna().all() else datetime.now().date()
    dt_max = df["DT_OBJ"].max().date() if "DT_OBJ" in df and not df["DT_OBJ"].isna().all() else datetime.now().date()
    
    with f1: datas_sel = st.date_input("Período", value=(dt_min, dt_max), format="DD/MM/YYYY")
    with f2:
        destinos = sorted(df["LOCAL_DESTINO"].unique())
        destinos_sel = st.multiselect("Locais", options=destinos, placeholder="Todos")
    with f3: search_term = st.text_input("Buscar Geral", placeholder="NF, Item, ID, OC...")

# --- ENGINE ---
df_filt = df.copy()

if isinstance(datas_sel, tuple) and len(datas_sel) == 2:
    start, end = datas_sel
    if "DT_OBJ" in df_filt.columns:
        df_filt = df_filt[(df_filt["DT_OBJ"].dt.date >= start) & (df_filt["DT_OBJ"].dt.date <= end)]

if destinos_sel:
    df_filt = df_filt[df_filt["LOCAL_DESTINO"].isin(destinos_sel)]

if search_term:
    t = search_term.lower()
    mask = (
        df_filt["DESCRICAO"].astype(str).str.lower().str.contains(t) |
        df_filt["NF"].astype(str).str.lower().str.contains(t) |
        df_filt["COD_ITEM"].astype(str).str.lower().str.contains(t) |
        df_filt["ID_PROCESSO"].astype(str).str.lower().str.contains(t) |
        df_filt["OC"].astype(str).str.lower().str.contains(t) # Adicionado busca por OC
    )
    df_filt = df_filt[mask]

st.divider()

if df_filt.empty:
    st.info("🔎 Nada encontrado.")
else:
    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    qtd_total = df_filt["QTD_FLOAT"].sum()
    valor_total = df_filt["VALOR_TOTAL_FLOAT"].sum()
    sem_dest = len(df_filt[df_filt["LOCAL_DESTINO"] == "Sem Destino"])
    
    k1.metric("📦 Volume (Qtd)", f"{int(qtd_total)}")
    k2.metric("💰 Valor Mercadoria", f"R$ {valor_total:,.2f}")
    k3.metric("📄 NFs", f"{df_filt['NF'].nunique()}")
    k4.metric("📍 Sem Destino", sem_dest, delta="Atenção" if sem_dest > 0 else "OK", delta_color="inverse")

    st.write("")
    
    c_graf, c_tab = st.columns([1, 1.5])
    
    with c_graf:
        st.subheader("🔥 Top Valor")
        df_tier = df_filt.groupby(["DESCRICAO", "LOCAL_DESTINO"])["VALOR_TOTAL_FLOAT"].sum().reset_index().sort_values("VALOR_TOTAL_FLOAT", ascending=False).head(10)
        fig = px.bar(df_tier, x="VALOR_TOTAL_FLOAT", y="DESCRICAO", orientation='h', text_auto='.2s', color="LOCAL_DESTINO", title="Top 10 Itens (R$)")
        fig.update_layout(yaxis={'categoryorder':'total ascending'}, legend=dict(orientation="h", y=1.02))
        st.plotly_chart(fig, use_container_width=True)

    with c_tab:
        st.subheader(f"📋 Lista ({len(df_filt)} itens)")
        st.caption("👆 Clique na linha para ver o rastro (OC, Motorista, Origem)")
        
        # Colunas Visíveis
        cols_view = ["ID_PROCESSO", "OC", "NF", "DESCRICAO", "QTD", "VALOR_TOTAL", "LOCAL_DESTINO"]
        cols_final = [c for c in cols_view if c in df_filt.columns]
        
        # Reset index é vital para a seleção funcionar certo após filtro
        df_display = df_filt.reset_index(drop=True)
        
        # TABELA COM EVENTO DE SELEÇÃO
        event = st.dataframe(
            df_display[cols_final],
            use_container_width=True,
            hide_index=True,
            height=400,
            on_select="rerun", # A Mágica acontece aqui
            selection_mode="single-row"
        )
        
        # LÓGICA DO CLIQUE
        if event.selection.rows:
            idx = event.selection.rows[0] # Pega o índice clicado
            item_selecionado = df_display.iloc[idx] # Pega os dados completos da linha (mesmo colunas ocultas)
            modal_rastro(item_selecionado) # Abre o modal