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
# 1. CONFIGURAÇÃO DA PÁGINA & CSS
# ==============================================================================
st.set_page_config(page_title="Controle de Estoque", page_icon="📦", layout="wide")

st.markdown("""
<style>

    /* Esconde Nav Nativa */
    [data-testid="stSidebarNav"] {display: none;}
    
    /* Card Estilo Executivo (Sem fundo & Responsivo) */
    .kpi-card {
        background-color: transparent;
        border-radius: 4px;
        padding: 15px 20px;
        margin-bottom: 20px;
        /* Sombra suave */
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
        /* Borda cinza translúcida */
        border: 1px solid rgba(128,128,128,0.2);
    }
    
    .kpi-label {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--text-color);
        opacity: 0.6;
        margin-bottom: 5px;
    }
    
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        color: var(--text-color);
        line-height: 1.2;
    }
    
    .kpi-sub {
        font-size: 12px;
        margin-top: 5px;
        color: #e74c3c;
    }
    
    /* --- BORDAS COLORIDAS --- */
    .border-white  { border-left: 5px solid var(--text-color); } 
    .border-red    { border-left: 5px solid #e74c3c; }
    .border-green  { border-left: 5px solid #2ecc71; }
    .border-blue   { border-left: 5px solid #3498db; }
    
    /* Ajustes Gerais */
    section[data-testid="stSidebar"] > div {height: 100vh; display: flex; flex-direction: column; justify-content: space-between; padding-top: 0px !important; padding-bottom: 20px !important;}
    div[data-testid="stSidebarUserContent"] {padding-top: 2rem !important; display: flex; flex-direction: column; height: 100%;}
    .footer-container { margin-top: auto; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. SIDEBAR
# ==============================================================================
with st.sidebar:
    
    # --- GRUPO SUPERIOR (Logo + Menu) ---
    # Não usamos st.container() aqui para deixar fluir no flex-start natural
    
    # 1. LOGO
    try:
        logo_path = "assets/logo.png"
        st.image(logo_path, use_container_width=True)
    except:
        st.header("MAROSO")

    # 2. MENU
    st.write("") 
    st.caption("MENU PRINCIPAL")
    
    st.page_link("pages/1_📊_Dashboard.py", label="Dashboard", icon="📊") 
    st.page_link("pages/2_🚛_Processo_Devolucao.py", label="Novo Processo", icon="🚛")
    st.page_link("pages/3_📋_Gestao_Tratativas.py", label="Gestão Tratativas", icon="📋")
    st.page_link("pages/4_📍_Posições.py", label="Posições & Rotas", icon="📍")
    st.page_link("pages/5_📦_Estoque_Destino.py", label="Estoque Destino", icon = "📦")

    # --- GRUPO INFERIOR (Perfil + Sair) ---
    # O CSS .footer-container (margin-top: auto) faz a mágica aqui
    st.markdown('<div class="footer-container">', unsafe_allow_html=True)
    
    st.markdown("---")
    
    c_perfil, c_texto = st.columns([0.25, 0.75])
    with c_perfil:
        st.markdown(
            """<div style='
                font-size: 24px; 
                text-align: center; 
                background: #262730; 
                border-radius: 50%; 
                width: 38px; 
                height: 38px; 
                display: flex; 
                align-items: center; 
                justify-content: center;
                border: 1px solid #444;
            '>👤</div>""", 
            unsafe_allow_html=True
        )
        
    with c_texto:
        usuario_nome = st.session_state.get('usuario', 'Admin').split(' ')[0].title()
        st.markdown(f"""
            <div style='line-height: 1.2;'>
                <span style='font-weight: bold; font-size: 14px;'>{usuario_nome}</span><br>
                <span style='font-size: 11px; color: #888;'>Maroso Transporte</span>
            </div>
        """, unsafe_allow_html=True)

    st.write("")
    
    if st.button("Sair do Sistema", use_container_width=True):
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

# ==============================================================================
# 4. INTERFACE PRINCIPAL
# ==============================================================================
st.title("Controle de Estoque por Destino")

try:
    df = carregar_dados_consolidados()
except Exception as e:
    st.error(f"Erro ao carregar: {e}")
    st.stop()

if df.empty:
    st.warning("📭 Nenhum dado encontrado.")
    st.stop()

# ==============================================================================
# 5. FILTROS GERAIS (Tudo no Topo para cruzar dados)
# ==============================================================================
with st.expander("🔍 Filtros & Visualização", expanded=True):
    f1, f2, f3 = st.columns([1, 1, 1.5])
    
    # 1. Filtro de Data
    with f1:
        dt_min = df["DT_OBJ"].min().date() if "DT_OBJ" in df and not df["DT_OBJ"].isna().all() else datetime.now().date()
        dt_max = df["DT_OBJ"].max().date() if "DT_OBJ" in df and not df["DT_OBJ"].isna().all() else datetime.now().date()
        datas_sel = st.date_input("Período", value=(dt_min, dt_max), format="DD/MM/YYYY")

    # 2. Filtro de Local (Trazido para cima)
    with f2:
        destinos = sorted(df["LOCAL_DESTINO"].unique())
        destinos_sel = st.multiselect("Locais", options=destinos, placeholder="Todos os locais")

    # 3. Busca Global (Trazido para cima)
    with f3:
        search_term = st.text_input("Busca Rápida", placeholder="NF, Item, OC, ID...")

# ==============================================================================
# 6. ENGINE DE FILTRAGEM (CRUZAMENTO)
# ==============================================================================
df_final = df.copy()

# A. Aplica Data
if isinstance(datas_sel, tuple) and len(datas_sel) == 2:
    start, end = datas_sel
    if "DT_OBJ" in df_final.columns:
        df_final = df_final[(df_final["DT_OBJ"].dt.date >= start) & (df_final["DT_OBJ"].dt.date <= end)]

# B. Aplica Local
if destinos_sel:
    df_final = df_final[df_final["LOCAL_DESTINO"].isin(destinos_sel)]

# C. Aplica Busca
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

# ==============================================================================
# 7. KPIs (CALCULADOS SOBRE OS DADOS CRUZADOS/FILTRADOS)
# ==============================================================================
st.write("") 
c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)

qtd_total = df_final["QTD_FLOAT"].sum()
valor_total = df_final["VALOR_TOTAL_FLOAT"].sum()
nfs_envolvidas = df_final["NF"].nunique()
sem_destino = len(df_final[df_final["LOCAL_DESTINO"] == "Sem Destino"])

def card_html(label, value, border_class, sub_html=""):
    return f"""
    <div class="kpi-card {border_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """

with c_kpi1:
    st.markdown(card_html("Volume Filtrado", f"{int(qtd_total)}", "border-white"), unsafe_allow_html=True)

with c_kpi2:
    st.markdown(card_html("Valor Filtrado", f"R$ {valor_total:,.2f}", "border-green"), unsafe_allow_html=True)

with c_kpi3:
    st.markdown(card_html("Processos / NFs", f"{nfs_envolvidas}", "border-blue"), unsafe_allow_html=True)

with c_kpi4:
    msg_dest = f"⚠️ {sem_destino} pendentes" if sem_destino > 0 else "Tudo Alocado"
    st.markdown(card_html("Sem Destino", f"{sem_destino}", "border-red", f"<div style='font-size:11px; margin-top:5px; color:#e74c3c'>{msg_dest}</div>" if sem_destino > 0 else ""), unsafe_allow_html=True)

# ==============================================================================
# 8. VISUALIZAÇÃO (TABELA EM CIMA, GRÁFICO EM BAIXO)
# ==============================================================================
st.divider()

if df_final.empty:
    st.info("🔎 Nenhum registro encontrado com esses filtros.")
else:
    # --- 1. TABELA (TOPO) ---
    st.subheader(f"📋 Lista Detalhada ({len(df_final)})")
    st.caption("👆 Clique na linha para ver detalhes")
    
    cols_view = ["ID_PROCESSO", "OC", "NF", "DESCRICAO", "QTD", "VALOR_TOTAL", "LOCAL_DESTINO"]
    cols_final = [c for c in cols_view if c in df_final.columns]
    
    df_display = df_final.reset_index(drop=True)
    
    event = st.dataframe(
        df_display[cols_final],
        use_container_width=True,
        hide_index=True,
        height=350,
        on_select="rerun",
        selection_mode="single-row"
    )
    
    if event.selection.rows:
        idx = event.selection.rows[0]
        item_selecionado = df_display.iloc[idx]
        modal_rastro(item_selecionado)

    st.write("")
    st.divider()

    # --- 2. GRÁFICO (EM BAIXO) ---
    st.subheader("🔥 Top Valor (Filtrado)")
    
    # Agrupa com base nos dados filtrados
    df_tier = df_final.groupby(["DESCRICAO", "LOCAL_DESTINO"])["VALOR_TOTAL_FLOAT"].sum().reset_index().sort_values("VALOR_TOTAL_FLOAT", ascending=False).head(10)
    
    if not df_tier.empty:
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
    else:
        st.info("Sem dados suficientes para o gráfico.")