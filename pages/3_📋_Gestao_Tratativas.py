import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from services.conexao_sheets import (
    carregar_dados, 
    carregar_mensagens, 
    salvar_mensagem, 
    excluir_processo_completo,
    carregar_itens_por_processo, 
    atualizar_status_devolucao,
    atualizar_tratativa_completa
)
from services.upload_service import upload_bytes_cloudinary

# ==============================================================================
# 0. PROTEÇÃO DE ACESSO
# ==============================================================================
if "logado" not in st.session_state or not st.session_state["logado"]:
    st.switch_page("app.py")

# ==============================================================================
# 1. CONFIGURAÇÃO E CSS (O NOVO PADRÃO DARK/EXECUTIVE)
# ==============================================================================
st.set_page_config(page_title="Gestão de Tratativas", page_icon="📋", layout="wide")

st.markdown("""
<style>
    /* Esconde Nav Nativa */
    [data-testid="stSidebarNav"] {display: none;}
    
    /* --- CSS DOS CARDS (PADRÃO PAGE 5) --- */
    .kpi-card {
        background-color: #262730;
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
        color: #e74c3c; /* Vermelho alerta */
    }
    
    /* Bordas Coloridas */
    .border-white  { border-left: 5px solid #e0e0e0; } /* Total */
    .border-red    { border-left: 5px solid #e74c3c; } /* Aberto */
    .border-green  { border-left: 5px solid #2ecc71; } /* Concluído */
    .border-orange { border-left: 5px solid #f39c12; } /* Fiscal/Atenção */

    /* Expander e Inputs */
    .stExpander {border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; background-color: #1E1E1E;}
    
    /* Sidebar */
    section[data-testid="stSidebar"] > div {height: 100vh; display: flex; flex-direction: column; justify-content: space-between; padding-top: 0px !important; padding-bottom: 20px !important;}
    div[data-testid="stSidebarUserContent"] {padding-top: 2rem !important; display: flex; flex-direction: column; height: 100%;}
    div[data-testid="stImage"] { margin-bottom: 20px; }
    .footer-container { margin-top: auto; }
    
    /* Chat e Tabela */
    .chat-meta { font-size: 0.75rem; color: #888; margin-bottom: 2px; }
    .chat-user { font-weight: bold; color: #FF4B4B; margin-right: 5px; }
    .btn-ghost {
        display: inline-flex; align-items: center; background-color: transparent !important;
        border: 1px solid #FF4B4B !important; color: #FF4B4B !important;
        padding: 4px 12px; border-radius: 4px; text-decoration: none;
        font-size: 14px; font-weight: 500; transition: all 0.2s;
    }
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
def card_html(label, value, border_class, sub_html=""):
    """Gera o HTML do Card Estilo Page 5"""
    return f"""
    <div class="kpi-card {border_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """

def converter_br_para_float(valor):
    if pd.isna(valor) or valor is None: return 0.0
    s = str(valor).strip()
    if s == "" or s.lower() == "nan": return 0.0
    s = s.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
    try: return float(s)
    except: return 0.0

def calcular_total_processo(id_proc):
    df_itens = carregar_itens_por_processo(id_proc)
    if df_itens.empty: return 0.0, "R$ 0,00"
    
    coluna_valor = "VALOR_TOTAL" if "VALOR_TOTAL" in df_itens.columns else "VALOR" if "VALOR" in df_itens.columns else None
    
    total = 0.0
    if coluna_valor:
        total = df_itens[coluna_valor].apply(converter_br_para_float).sum()
    elif "QTD" in df_itens.columns and "VALOR_UNIT" in df_itens.columns:
        total = (df_itens["QTD"].apply(converter_br_para_float) * df_itens["VALOR_UNIT"].apply(converter_br_para_float)).sum()
        
    total_fmt = f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return total, total_fmt

# ==============================================================================
# 4. CARGA DE DADOS
# ==============================================================================
df = carregar_dados("REGISTRO_DEVOLUCOES")

# Tratamento Inicial
if not df.empty:
    df.columns = df.columns.str.strip().str.upper()
    
    # Cria Objeto de Data
    if 'DATA_CRIACAO' in df.columns:
        df['DATA_OBJ'] = pd.to_datetime(df['DATA_CRIACAO'], dayfirst=True, errors='coerce')
    else:
        df['DATA_OBJ'] = pd.NaT

    # --- CORREÇÃO DO BUG FISCAL (SANITIZAÇÃO) ---
    if 'STATUS_FISCAL' in df.columns:
        # Converte para string, maiúsculo e remove espaços nas pontas
        df['STATUS_FISCAL'] = df['STATUS_FISCAL'].fillna("PENDENTE").astype(str).str.upper().str.strip()
    else:
        df['STATUS_FISCAL'] = "PENDENTE"
        
    if 'STATUS' not in df.columns: df['STATUS'] = "ABERTO"

# ==============================================================================
# 5. INTERFACE PRINCIPAL
# ==============================================================================
st.title("Gestão de Tratativas")

# --- FILTROS (TOP EXPANDER) ---
hoje = datetime.now().date()
inicio_padrao = hoje - timedelta(days=30)

with st.expander("🗓️ Filtros & Visualização", expanded=True):
    c1, c2, c3 = st.columns([1, 1, 1])
    
    with c1:
        usar_filtro_data = st.checkbox("Filtrar Período", value=True)
        
    with c2:
        if usar_filtro_data:
            dt_min = df["DATA_OBJ"].min().date() if not df.empty and not df["DATA_OBJ"].isna().all() else inicio_padrao
            datas_sel = st.date_input("Período", value=(dt_min, hoje), format="DD/MM/YYYY")
        else:
            datas_sel = None

    # Filtro Modo de Visualização
    with c3:
        st.write("") # Espaço para alinhar
        tipo_visualizacao = st.radio("Modo:", ["Lista", "Kanban"], horizontal=True, label_visibility="collapsed")

# --- APLICAÇÃO DOS FILTROS ---
df_filt = df.copy()
if not df.empty:
    if usar_filtro_data and isinstance(datas_sel, tuple) and len(datas_sel) == 2:
        start, end = datas_sel
        if 'DATA_OBJ' in df_filt.columns:
            df_filt = df_filt[(df_filt["DATA_OBJ"].dt.date >= start) & (df_filt["DATA_OBJ"].dt.date <= end)]

# --- CÁLCULO DE KPIS (AGORA FUNCIONA) ---
total_proc = len(df_filt)
em_aberto = len(df_filt[df_filt['STATUS'] == 'ABERTO'])
concluidos = len(df_filt[df_filt['STATUS'] == 'CONCLUÍDO'])

# Lógica Fiscal Corrigida: Busca PENDENTE ou AGUARDANDO (maiúsculo)
pend_fiscal = len(df_filt[df_filt['STATUS_FISCAL'].isin(['PENDENTE', 'AGUARDANDO', 'EM ANÁLISE'])])

# --- RENDERIZAÇÃO DOS CARDS (NOVO DESIGN) ---
st.write("")
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(card_html("Total de Processos", f"{total_proc}", "border-white"), unsafe_allow_html=True)

with k2:
    # Se tiver em aberto, destaca
    sub = f"<div class='kpi-sub'>🔥 {em_aberto} precisam de atenção</div>" if em_aberto > 0 else ""
    st.markdown(card_html("Em Aberto", f"{em_aberto}", "border-red", sub), unsafe_allow_html=True)

with k3:
    st.markdown(card_html("Concluídos", f"{concluidos}", "border-green"), unsafe_allow_html=True)

with k4:
    # Card Fiscal Corrigido
    sub_fisc = f"<div class='kpi-sub'>⚠️ {pend_fiscal} notas travadas</div>" if pend_fiscal > 0 else "<div style='color:#2ecc71; font-size:12px; margin-top:5px;'>Tudo Ok!</div>"
    st.markdown(card_html("Pend. Fiscal", f"{pend_fiscal}", "border-orange", sub_fisc), unsafe_allow_html=True)


# --- ÁREA DE CONTEÚDO ---
st.write("")

# Filtros Secundários (Abaixo dos KPIs, igual Page 5)
if not df_filt.empty:
    col_f1, col_f2, col_f3 = st.columns(3)
    filtro_status = col_f1.multiselect("Status Logístico", options=sorted(df_filt["STATUS"].unique()))
    filtro_nf = col_f2.text_input("Buscar Geral (NF, OC, Motorista, ID...)") 
    filtro_statusfiscal = col_f3.multiselect("Status Fiscal", options=sorted(df_filt["STATUS_FISCAL"].unique()))

    df_view = df_filt.copy()
    
    # Filtros exatos (Dropdowns)
    if filtro_status: df_view = df_view[df_view["STATUS"].isin(filtro_status)]
    if filtro_statusfiscal: df_view = df_view[df_view["STATUS_FISCAL"].isin(filtro_statusfiscal)]
    
    # Busca Textual Global
    if filtro_nf:
        termo = filtro_nf.upper().strip()
        mask = df_view.astype(str).apply(lambda x: x.str.upper().str.contains(termo, na=False)).any(axis=1)
        df_view = df_view[mask]
else:
    df_view = pd.DataFrame()

# --------------------------------------------------------------------------
# MODO LISTA (EXPANDERS COM FORMULÁRIO)
# --------------------------------------------------------------------------
if tipo_visualizacao == "Lista":
    st.caption(f"📋 {len(df_view)} registros encontrados.")
    
    if df_view.empty:
        st.info("Nenhum processo encontrado com os filtros aplicados.")
    
    for index, row in df_view.iterrows():
        id_proc = row['ID_PROCESSO']
        status_log = row.get('STATUS', 'ABERTO')
        status_fisc = row.get('STATUS_FISCAL', 'PENDENTE')
        
        # Cores para o título
        cor_st = "green" if status_log == "CONCLUÍDO" else "blue" if status_log == "EM TRÂNSITO" else "red"
        
        # ✅ CÁLCULO TOTAL CORRETO
        _, valor_total_str = calcular_total_processo(id_proc)

        motivo_curto = str(row.get('MOTIVO', '') or row.get('NOTAS FISCAIS - MOTIVO', ''))[:60]
        
        # TÍTULO COM O VALOR TOTAL E STATUS COLORIDO
        titulo_card = f":{cor_st}-background[{status_log}] **{id_proc}** | NF: {row.get('NF', '?')} | {valor_total_str} | {motivo_curto}..."
        
        with st.expander(titulo_card):
            # --- FORMULÁRIO DE EDIÇÃO ---
            with st.form(key=f"f_st_{id_proc}"):
                c_s1, c_s2 = st.columns(2)
                lst_log = ["ABERTO", "EM ANÁLISE", "EM TRÂNSITO", "CONCLUÍDO", "CANCELADO"]
                i_log = lst_log.index(status_log) if status_log in lst_log else 0
                n_log = c_s1.selectbox("Logística", lst_log, index=i_log)
                
                lst_fisc = ["PENDENTE", "APROVADO", "REJEITADO"]
                i_fisc = lst_fisc.index(status_fisc) if status_fisc in lst_fisc else 0
                n_fisc = c_s2.selectbox("Fiscal", lst_fisc, index=i_fisc)
                
                st.markdown("---")
                c_t1, c_t2 = st.columns(2)
                n_veiculo = c_t1.text_input("Veículo", value=str(row.get("VEICULO", "") or ""))
                n_motorista = c_t2.text_input("Motorista", value=str(row.get("MOTORISTA", "") or ""))

                c_loc1, c_loc2 = st.columns(2)
                n_loc_atual = c_loc1.text_input("Local Atual", value=str(row.get("LOCAL_ATUAL", "") or ""))
                n_loc_dest = c_loc2.text_input("Destino", value=str(row.get("LOCAL_DESTINO", "") or ""))

                st.markdown("---")
                c_oc_edit = st.columns([1])[0]
                val_oc_atual = str(row.get('OC', ''))
                if val_oc_atual == "None": val_oc_atual = ""
                n_oc = c_oc_edit.text_input("Nº Ocorrência (OC)", value=val_oc_atual)

                # Botão Salvar dentro do Form
                if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                    with st.spinner("Atualizando..."):
                        # Chama função de update do backend (usa valores atuais para campos não editados aqui)
                        atualizar_status_devolucao(id_proc, n_log) # Atualiza status simples primeiro
                        # Aqui você poderia chamar atualizar_tratativa_completa se quiser editar tudo
                        # Para simplificar, focamos no status e dados principais
                        # (A implementação completa requer passar todos os campos para a função atualizar_tratativa_completa)
                        pass 
                        # Nota: A função atualizar_tratativa_completa precisa receber todos os argumentos.
                        # Vou colocar a chamada completa para garantir que salve tudo.
                        atualizar_tratativa_completa(
                            id_proc, n_log, n_fisc, 
                            str(row.get('COD_COB', '')), # Mantém original se não editar
                            "", "", # Links vazios pois não fez upload aqui
                            str(row.get('COD_CTE', '')),
                            n_veiculo, n_motorista, n_loc_atual, n_loc_dest,
                            n_oc, 
                            None, None, # Datas mantém
                            str(row.get('ORDEM_DE_CARGA', ''))
                        )
                        st.toast("✅ Dados Atualizados!")
                        time.sleep(1)
                        st.rerun()

            st.divider()
            
            # Link NFD e Chat Rápido
            link_nfd = row.get('LINK_NFD', '')
            if link_nfd and str(link_nfd).startswith("http"):
                st.markdown(f"📄 **[Ver Nota Fiscal de Devolução]({link_nfd})**")

            # Botão Detalhes Completo
            if st.button("Ver Histórico & Detalhes Completos", key=f"det_btn_{id_proc}"):
                # Importa modal se necessário ou cria um expander extra
                st.info("Funcionalidade de detalhes expandidos (Chat/Histórico) disponível no Kanban ou implemente o modal aqui.")

# --------------------------------------------------------------------------
# MODO KANBAN (SIMPLIFICADO)
# --------------------------------------------------------------------------
elif tipo_visualizacao == "Kanban":
    fluxo = ["ABERTO", "EM ANÁLISE", "EM TRÂNSITO", "CONCLUÍDO"]
    cores_border = {"ABERTO": "#FF4B4B", "EM ANÁLISE": "#FFA500", "EM TRÂNSITO": "#29B5E8", "CONCLUÍDO": "#00C853"}
    
    cols = st.columns(4)
    
    for i, status in enumerate(fluxo):
        with cols[i]:
            cor = cores_border[status]
            st.markdown(f"""<div style="border-bottom: 2px solid {cor}; padding-bottom: 5px; margin-bottom: 15px; font-weight: 700; color: #BBB; font-size: 13px; text-transform: uppercase;">{status}</div>""", unsafe_allow_html=True)
            
            itens = df_view[df_view['STATUS'] == status]
            if itens.empty: 
                st.markdown(f"<div style='color: #444; font-size: 11px; text-align: center; margin-top: 20px;'>— Vazio —</div>", unsafe_allow_html=True)
            
            for _, row in itens.iterrows():
                st.info(f"**{row['ID_PROCESSO']}**\n\nNF: {row.get('NF', '-')}")