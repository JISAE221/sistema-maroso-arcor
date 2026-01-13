import streamlit as st
import pandas as pd
import time
from datetime import datetime
from services.conexao_sheets import carregar_dados, atualizar_status_devolucao

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Dashboard - Maroso", page_icon="📊", layout="wide")

# ==============================================================================
# 2. PROTEÇÃO DE ACESSO
# ==============================================================================
if "logado" not in st.session_state or not st.session_state["logado"]:
    st.warning("Acesso não autorizado.")
    st.switch_page("app.py")

# ==============================================================================
# FUNÇÃO DO MODAL
# ==============================================================================
@st.dialog("Detalhes do Processo")
def modal_detalhes_completo(id_proc, row, usuario_ativo):
    st.markdown(f"### Processo: **{id_proc}**")
    
    # 1. Status Principal
    st.caption("Status Atual")
    status_atual = row.get('STATUS', 'ABERTO')
    cor_st = "green" if status_atual == "CONCLUÍDO" else "blue" if status_atual == "EM TRÂNSITO" else "orange"
    st.markdown(f":{cor_st}[**{status_atual}**]")
    
    st.divider()
    
    # 2. Informações Principais
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Ordem de Carga**")
        st.info(f"{row.get('ORDEM_DE_CARGA', '-')}")

        st.markdown("**Ocorrência**")
        st.info(f"{row.get('OC', '-')}")
        
    with c2:
        st.markdown("**Responsável**")
        st.write(f"{row.get('RESPONSAVEL', '-')}")
        
        st.markdown("**Local/Cliente**")
        st.write(f"{row.get('LOCAL', '-')}")

    # 3. Logística e Rota
    st.divider()
    st.markdown("#### Logística")
    
    col_mot, col_veic = st.columns(2)
    col_mot.text_input("Motorista", value=str(row.get('MOTORISTA', '')), disabled=True)
    col_veic.text_input("Veículo/Placa", value=str(row.get('VEICULO', '')), disabled=True)
    
    st.write("")
    st.markdown(f"**Rota:** `{row.get('LOCAL_ATUAL', 'Origem')}` ➝ `{row.get('LOCAL_DESTINO', 'Destino')}`")

    # 4. Status Fiscal
    st.divider()
    st_fiscal = row.get('STATUS_FISCAL', 'PENDENTE')
    icone_fiscal = "✅" if "APROVADO" in st_fiscal else "⚠️" if "PENDENTE" in st_fiscal else "❌"
    st.markdown(f"**Status Fiscal:** {icone_fiscal} {st_fiscal}")

    st.write("")
    if st.button("Fechar", use_container_width=True):
        st.rerun()

# ==============================================================================
# 3. CSS GERAL (Refinado)
# ==============================================================================
st.markdown("""
<style>
    /* --- SIDEBAR --- */
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"] > div {
        height: 100vh;
        display: flex; flex-direction: column; justify-content: space-between;
        padding-bottom: 20px !important;
    }
    
    /* --- HEADER DE BOAS VINDAS --- */
    .welcome-container {
        background-color: var(--secondary-background-color);
        padding: 20px 25px; border-radius: 10px;
        border-left: 5px solid #FF4B4B;
        margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .welcome-text h2 { margin: 0; font-size: 24px; font-weight: 700; }
    .welcome-text p { margin: 2px 0 0 0; font-size: 14px; opacity: 0.8; }
    .date-badge {
        background-color: rgba(128, 128, 128, 0.1); padding: 6px 14px; border-radius: 15px;
        font-size: 12px; font-weight: 600;
    }

    /* --- METRICS CARDS (PAGE 5 STYLE) --- */
    .stock-card {
        background-color: #f8f9fa; border: 1px solid #e9ecef;
        padding: 15px; border-radius: 8px; text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stock-value { font-size: 24px; font-weight: bold; color: #333; }
    .stock-label { font-size: 12px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; }

    /* --- KANBAN CARDS --- */
    .k-column-header {
        font-size: 12px; font-weight: 700; text-transform: uppercase;
        color: #888; border-bottom: 2px solid #ccc; padding-bottom: 8px;
        margin-bottom: 20px; letter-spacing: 1px;
    }
    .kanban-card {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 8px; padding: 12px; margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .kanban-card:hover {
        transform: translateY(-2px); border-color: rgba(128, 128, 128, 0.4);
    }
    .k-card-header {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 8px; padding-bottom: 8px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.1);
    }
    .k-id { font-weight: 800; font-size: 13px; }
    .k-fiscal-badge {
        font-size: 10px; padding: 2px 6px; border-radius: 4px;
        font-weight: 700; text-transform: uppercase;
    }
    .k-body { font-size: 12px; opacity: 0.9; }
    .k-row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
    
    /* --- ROTA BOX CORRIGIDA --- */
    .k-rota-box {
        background-color: rgba(128, 128, 128, 0.05);
        border-radius: 4px; padding: 6px; margin-top: 8px;
        font-size: 11px;
    }
    .k-rota-title { font-weight: 700; color: #29B5E8; margin-bottom: 2px; }
    .k-rota-flow { display: flex; align-items: center; gap: 4px; color: #888; }
    
    .k-time { font-size: 10px; color: #888; margin-top: 8px; text-align: right; font-style: italic; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 4. SIDEBAR
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
# 5. CARREGAMENTO E PREPARAÇÃO DE DADOS
# ==============================================================================
df = carregar_dados("REGISTRO_DEVOLUCOES")

# Inicializa variáveis zeradas
total_aberto = total_concluido = pendencia_fiscal = total_atrasados = 0
destinos_populares = "N/A"
itens_em_armazem = 0
eficiencia_media = "0d"

if not df.empty:
    df.columns = df.columns.str.strip().str.upper()
    
    # --- KPIs GERAIS (Page 1 Originais) ---
    total_aberto = len(df[df['STATUS'] == 'ABERTO']) if 'STATUS' in df.columns else 0
    total_concluido = len(df[df['STATUS'] == 'CONCLUÍDO']) if 'STATUS' in df.columns else 0
    
    if 'STATUS_FISCAL' in df.columns:
        pendencia_fiscal = len(df[df['STATUS_FISCAL'].astype(str).str.contains('AGUARDANDO|PENDENTE', na=False)])
    
    # Cálculo de atraso
    if 'DATA_CRIACAO' in df.columns and 'STATUS' in df.columns:
        df['DATA_OBJ'] = pd.to_datetime(df['DATA_CRIACAO'], dayfirst=True, errors='coerce')
        mask_vencidos = (df['STATUS'] != 'CONCLUÍDO') & ((pd.Timestamp.now() - df['DATA_OBJ']).dt.days > 7)
        total_atrasados = len(df[mask_vencidos])
    
    # --- KPIs DE ESTOQUE/DESTINO (Elementos da Page 5) ---
    # Simulando métricas de destino com base nos dados existentes
    if 'LOCAL_DESTINO' in df.columns:
        destinos = df['LOCAL_DESTINO'].value_counts()
        destinos_populares = destinos.index[0] if not destinos.empty else "N/A"
    
    # Simulando Itens em Armazém (Ex: Status Concluído ou Local Atual = CD)
    itens_em_armazem = len(df[df['LOCAL_ATUAL'].astype(str).str.contains('CD|ARMAZEM|MATRIZ', case=False, na=False)])

hora = datetime.now().hour
saudacao = "Bom dia" if 5 <= hora < 12 else "Boa tarde" if 12 <= hora < 18 else "Boa noite"
cargo_user = st.session_state.get('cargo', 'Colaborador')

# ==============================================================================
# 6. LAYOUT DO DASHBOARD
# ==============================================================================

# --- HEADER ---
st.markdown(f"""
<div class="welcome-container">
    <div class="welcome-text">
        <h2>{saudacao}, {usuario_nome}!</h2>
        <p>Painel de Controle Unificado (Dashboard Geral + Estoque Destino)</p>
    </div>
    <div class="date-badge">📅 {datetime.now().strftime('%d/%m/%Y')}</div>
</div>
""", unsafe_allow_html=True)

# --- BLOCÃO DE KPIs (Misturando Page 1 e Page 5) ---
st.markdown("#### 📊 Visão Geral do Processo")
k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("📦 Aberto (Fila)", total_aberto, delta_color="off")
k2.metric("⚖️ Pend. Fiscal", pendencia_fiscal, delta="Atenção", delta_color="inverse")
k3.metric("🔥 Atrasados (>7d)", total_atrasados, delta="Crítico", delta_color="inverse")
k4.metric("🏢 Itens no CD", itens_em_armazem, help="Baseado no Local Atual")
k5.metric("🏁 Top Destino", destinos_populares, help="Destino mais frequente")

st.divider()

# ==============================================================================
# 7. KANBAN DETALHADO (HTML CORRIGIDO)
# ==============================================================================
if not df.empty and 'STATUS' in df.columns:
    st.subheader("📌 Fluxo de Trabalho")
    
    fluxo = ["ABERTO", "EM ANÁLISE", "EM TRÂNSITO", "CONCLUÍDO"]
    cores_coluna = {"ABERTO": "#FF4B4B", "EM ANÁLISE": "#FFA726", "EM TRÂNSITO": "#29B5E8", "CONCLUÍDO": "#00C853"}
    
    cols = st.columns(4)
    
    for i, status in enumerate(fluxo):
        with cols[i]:
            # Cabeçalho da Coluna
            cor = cores_coluna[status]
            st.markdown(f"<div class='k-column-header' style='border-color: {cor}; color: {cor};'>{status}</div>", unsafe_allow_html=True)
            
            # Filtra itens
            itens = df[df['STATUS'] == status]
            
            if itens.empty: 
                st.markdown("<div style='text-align: center; color: #888; font-size: 12px; margin-top: 10px;'>— Vazio —</div>", unsafe_allow_html=True)
            
            # LOOP DOS CARDS
            for _, row in itens.tail(5).iterrows():
                id_proc = row.get('ID_PROCESSO', '?')
                
                # --- PREPARA DADOS ---
                st_fiscal = row.get('STATUS_FISCAL', 'PENDENTE')
                # Cores Badge Fiscal
                bg_fisc = "#e0f2f1" if "APROVADO" in st_fiscal else "#ffebee" if "REJEITADO" in st_fiscal else "#fff3e0" if "AGUARDANDO" in st_fiscal else "#f5f5f5"
                fg_fisc = "#00695c" if "APROVADO" in st_fiscal else "#c62828" if "REJEITADO" in st_fiscal else "#ef6c00" if "AGUARDANDO" in st_fiscal else "#616161"
                
                nf_val = row.get('NF', '-')
                resp_val = str(row.get('RESPONSAVEL', 'System')).split(' ')[0].title()
                
                # Dados Transporte
                veic = str(row.get('VEICULO', ''))
                mot = str(row.get('MOTORISTA', '')).split(' ')[0].title()
                loc_atual = str(row.get('LOCAL_ATUAL', '...'))
                loc_dest = str(row.get('LOCAL_DESTINO', '...'))
                
                info_transporte = ""
                if veic and mot: info_transporte = f"{veic} • {mot}"
                elif mot: info_transporte = mot
                
                # Tempo
                dias_aberto = 0
                str_tempo = "Hoje"
                if 'DATA_OBJ' in df.columns and not pd.isna(row['DATA_OBJ']):
                     dias_aberto = (datetime.now() - row['DATA_OBJ']).days
                     str_tempo = f"há {dias_aberto}d"
                icon_time = "🔥" if dias_aberto > 7 else "🕒"

                # --- HTML DA ROTA (SANEADO) ---
                # Importante: Mantemos tudo alinhado à esquerda na string para evitar quebras
                html_rota = ""
                if loc_atual != '...' and loc_atual != '':
                    html_rota = f"""
                    <div class="k-rota-box">
                        <div class="k-rota-title">🚛 {info_transporte if info_transporte else 'Transporte'}</div>
                        <div class="k-rota-flow">
                            <span>{loc_atual}</span> <span style="color:#FF4B4B; font-weight:bold;">➝</span> <span>{loc_dest}</span>
                        </div>
                    </div>"""

                # --- HTML DO CARD (SANEADO) ---
                html_card = f"""
                <div class="kanban-card">
                    <div class="k-card-header">
                        <span class="k-id">{id_proc}</span>
                        <span class="k-fiscal-badge" style="background-color: {bg_fisc}; color: {fg_fisc}; border: 1px solid {fg_fisc}40;">
                            {st_fiscal}
                        </span>
                    </div>
                    <div class="k-body">
                        <div class="k-row"><span class="k-icon" style="margin-right: 5px;">📄</span><strong>{nf_val}</strong></div>
                        <div class="k-row"><span class="k-icon" style="margin-right: 5px;">👤</span><span>{resp_val}</span></div>
                        {html_rota}
                    </div>
                    <div class="k-time">{icon_time} {str_tempo}</div>
                </div>
                """
                
                st.markdown(html_card, unsafe_allow_html=True)
                
                # --- BOTÕES DE AÇÃO ---
                c_esq, c_meio, c_dir = st.columns([1, 4.5, 1])
                
                # 1. BOTÃO VOLTAR
                if i > 0:
                    if c_esq.button("◀", key=f"d_prev_{id_proc}", help="Voltar Etapa"):
                        try:
                            atualizar_status_devolucao(id_proc, fluxo[i-1])
                            st.toast(f"Movido para {fluxo[i-1]}")
                            time.sleep(0.5)
                            st.rerun()
                        except: pass
                
                # 2. BOTÃO DETALHES
                if c_meio.button("Detalhes", key=f"d_det_{id_proc}", use_container_width=True):
                    try:
                        modal_detalhes_completo(id_proc, row, st.session_state.get('usuario', 'Anon'))
                    except NameError:
                        st.switch_page("pages/3_📋_Gestao_Tratativas.py")

                # 3. BOTÃO AVANÇAR
                if i < len(fluxo) - 1:
                    if c_dir.button("▶", key=f"d_next_{id_proc}", help="Avançar Etapa"):
                        try:
                            atualizar_status_devolucao(id_proc, fluxo[i+1])
                            st.toast(f"Movido para {fluxo[i+1]}")
                            time.sleep(0.5)
                            st.rerun()
                        except: pass
                
                st.write("")

else:
    st.info("Nenhum dado encontrado para gerar o dashboard.")