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
# 1. CONFIGURAÇÃO DA PÁGINA & CSS (ESTILO PAGE 3)
# ==============================================================================
st.set_page_config(page_title="Controle de Estoque", page_icon="📦", layout="wide")

st.markdown("""
<style>
    /* Esconde Nav Nativa */
    [data-testid="stSidebarNav"] {display: none;}
    
    /* --- CSS DOS CARDS (IGUAL PAGE 3) --- */
    .kpi-card {
        background-color: #262730; /* Fundo escuro padrão */
        border-radius: 4px;
        padding: 15px 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.05);
    }
    .kpi-label {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #a0a0a0;
        margin-bottom: 5px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.2;
    }
    .kpi-sub {
        font-size: 12px;
        margin-top: 5px;
        color: #e74c3c; /* Cor de alerta padrão */
    }
    
    /* Bordas Coloridas */
    .border-white { border-left: 5px solid #e0e0e0; }
    .border-green { border-left: 5px solid #2ecc71; }
    .border-blue  { border-left: 5px solid #3498db; }
    .border-red   { border-left: 5px solid #e74c3c; }

    /* Ajuste Sidebar */
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
# 3. FUNÇÕES E CARGA
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

    cols_capa = [col_id_proc, "LOCAL_DESTINO", "NF", "VEICULO", "DATA_EMISSAO", "STATUS", "OC", "MOTORISTA", "STATUS_FISCAL"]
    cols_existentes = [c for c in cols_capa if c in df_processos.columns]
    
    df_full = pd.merge(df_itens, df_processos[cols_existentes], left_on=col_id_item, right_on=col_id_proc, how="inner")
    
    if "LOCAL_DESTINO" in df_full.columns:
        df_full["LOCAL_DESTINO"] = df_full["LOCAL_DESTINO"].fillna("Sem Destino").replace("", "Sem Destino")
    
    if "DATA_EMISSAO" in df_full.columns:
        df_full["DT_OBJ"] = pd.to_datetime(df_full["DATA_EMISSAO"], dayfirst=True, errors='coerce')
    
    return df_full

@st.dialog("🕵️ Rastro Detalhado do Item", width="large")
def modal_rastro(item):
    st.markdown(f"### {item.get('DESCRICAO', 'Item')}")
    st.caption(f"Cód: {item.get('COD_ITEM', '-')}")
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Processo ID", item.get('ID_PROCESSO', '-'))
    c2.metric("Nota Fiscal", item.get('NF', '-'))
    c3.metric("Ocorrência (OC)", item.get('OC', '-'))
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
    if st.button("Fechar Detalhes", use_container_width=True):
        st.rerun()

# ==============================================================================
# 4. INTERFACE PRINCIPAL
# ==============================================================================
# Título Clean
st.title("Controle de Estoque por Destino")

try:
    df = carregar_dados_consolidados()
except Exception as e:
    st.error(f"Erro ao carregar: {e}")
    st.stop()

if df.empty:
    st.warning("📭 Nenhum dado encontrado.")
    st.stop()

# --- 1. FILTRO DE DATA (EXPANDER) ---
with st.expander("🗓️ Filtros & Visualização", expanded=True):
    col_data, col_vazia = st.columns([1, 2])
    with col_data:
        dt_min = df["DT_OBJ"].min().date() if "DT_OBJ" in df and not df["DT_OBJ"].isna().all() else datetime.now().date()
        dt_max = df["DT_OBJ"].max().date() if "DT_OBJ" in df and not df["DT_OBJ"].isna().all() else datetime.now().date()
        datas_sel = st.date_input("Filtrar Período", value=(dt_min, dt_max), format="DD/MM/YYYY")

# APLICA FILTRO DE DATA (GLOBAL)
df_date_filt = df.copy()
if isinstance(datas_sel, tuple) and len(datas_sel) == 2:
    start, end = datas_sel
    if "DT_OBJ" in df_date_filt.columns:
        df_date_filt = df_date_filt[(df_date_filt["DT_OBJ"].dt.date >= start) & (df_date_filt["DT_OBJ"].dt.date <= end)]

# --- 2. CARDS DE KPI (LAYOUT IGUAL PAGE 3) ---
# Calculamos os KPIs com base no filtro de DATA (pra dar visão macro do período)
qtd_total = df_date_filt["QTD_FLOAT"].sum()
valor_total = df_date_filt["VALOR_TOTAL_FLOAT"].sum()
nfs_envolvidas = df_date_filt["NF"].nunique()
sem_destino = len(df_date_filt[df_date_filt["LOCAL_DESTINO"] == "Sem Destino"])

st.write("") # Espaço
c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)

def card_html(label, value, border_class, sub_html=""):
    return f"""
    <div class="kpi-card {border_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """

with c_kpi1:
    st.markdown(card_html("Volume Total (Qtd)", f"{int(qtd_total)}", "border-white"), unsafe_allow_html=True)

with c_kpi2:
    st.markdown(card_html("Valor em Mercadoria", f"R$ {valor_total:,.2f}", "border-green"), unsafe_allow_html=True)

with c_kpi3:
    st.markdown(card_html("Processos / NFs", f"{nfs_envolvidas}", "border-blue"), unsafe_allow_html=True)

with c_kpi4:
    # Se tiver sem destino, mostra em vermelho
    alerta = f"<div class='kpi-sub'>⚠️ {sem_destino} não alocados</div>" if sem_destino > 0 else ""
    st.markdown(card_html("Pend. de Destino", f"{sem_destino}", "border-red", alerta), unsafe_allow_html=True)


# --- 3. BARRA DE FILTROS CLEAN (ABAIXO DOS KPIS) ---
st.write("")
c_filt1, c_filt2 = st.columns([1, 2])

with c_filt1:
    destinos = sorted(df_date_filt["LOCAL_DESTINO"].unique())
    destinos_sel = st.multiselect("Locais de Destino", options=destinos, placeholder="Todos os locais")

with c_filt2:
    search_term = st.text_input("Buscar Geral (NF, Item, OC, ID...)", placeholder="Digite para pesquisar...")

# --- APLICAÇÃO DOS FILTROS FINAIS ---
df_final = df_date_filt.copy()

if destinos_sel:
    df_final = df_final[df_final["LOCAL_DESTINO"].isin(destinos_sel)]

if search_term:
    t = search_term.lower()
    mask = (
        df_final["DESCRICAO"].astype(str).str.lower().str.contains(t) |
        df_final["NF"].astype(str).str.lower().str.contains(t) |
        df_final["COD_ITEM"].astype(str).str.lower().str.contains(t) |
        df_final["ID_PROCESSO"].astype(str).str.lower().str.contains(t) |
        df_final["OC"].astype(str).str.lower().str.contains(t)
    )
    df_final = df_final[mask]

# --- 4. GRÁFICOS E TABELA ---
st.divider()

if df_final.empty:
    st.info("🔎 Nenhum registro encontrado com esses filtros.")
else:
    c_graf, c_tab = st.columns([1, 1.5])
    
    with c_graf:
        st.subheader("🔥 Top Valor em Estoque")
        df_tier = df_final.groupby(["DESCRICAO", "LOCAL_DESTINO"])["VALOR_TOTAL_FLOAT"].sum().reset_index().sort_values("VALOR_TOTAL_FLOAT", ascending=False).head(10)
        
        fig = px.bar(
            df_tier, 
            x="VALOR_TOTAL_FLOAT", 
            y="DESCRICAO", 
            orientation='h', 
            text_auto='.2s', 
            color="LOCAL_DESTINO", 
            title=""
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=20, b=0),
            yaxis={'categoryorder':'total ascending'}, 
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)

    with c_tab:
        st.subheader(f"📋 Lista Detalhada ({len(df_final)})")
        st.caption("👆 Clique na linha para ver o rastro")
        
        cols_view = ["ID_PROCESSO", "OC", "NF", "DESCRICAO", "QTD", "VALOR_TOTAL", "LOCAL_DESTINO"]
        cols_final = [c for c in cols_view if c in df_final.columns]
        
        df_display = df_final.reset_index(drop=True)
        
        event = st.dataframe(
            df_display[cols_final],
            use_container_width=True,
            hide_index=True,
            height=400,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        if event.selection.rows:
            idx = event.selection.rows[0]
            item_selecionado = df_display.iloc[idx]
            modal_rastro(item_selecionado)