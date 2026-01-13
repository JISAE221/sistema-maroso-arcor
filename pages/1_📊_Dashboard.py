import streamlit as st
import pandas as pd
import time
import pytz # Importante para fuso horário
from datetime import datetime
from services.conexao_sheets import carregar_dados, atualizar_status_devolucao

# ==============================================================================
# 0. CONFIGURAÇÕES GLOBAIS & FUSO HORÁRIO
# ==============================================================================
# Define fuso horário BR para corrigir distorção de horário do servidor
FUSO_BR = pytz.timezone('America/Sao_Paulo')

st.set_page_config(page_title="Dashboard - Maroso", page_icon="📊", layout="wide")

# ==============================================================================
# 1. CSS RESPONSIVO (LIGHT/DARK MODE & CARDS TRANSPARENTES)
# ==============================================================================
st.markdown("""
<style>
    /* --- SIDEBAR AJUSTADA --- */
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"] > div {
        height: 100vh; display: flex; flex-direction: column; justify-content: space-between;
        padding-bottom: 20px !important;
    }

    /* --- HEADER (Adaptação ao Tema) --- */
    .welcome-container {
        background-color: var(--secondary-background-color);
        padding: 20px 25px; border-radius: 12px;
        border-left: 5px solid #FF4B4B;
        margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .welcome-text h2 { margin: 0; font-size: 24px; font-weight: 700; color: var(--text-color); }
    .welcome-text p { margin: 2px 0 0 0; font-size: 14px; opacity: 0.8; color: var(--text-color); }
    .date-badge {
        background-color: var(--background-color); 
        border: 1px solid var(--text-color); opacity: 0.3;
        padding: 6px 14px; border-radius: 15px;
        font-size: 12px; font-weight: 600; color: var(--text-color);
    }

    /* --- KPI CARDS (Tipo Page 5) --- */
    div[data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        padding: 15px; border-radius: 10px;
        border: 1px solid rgba(128, 128, 128, 0.1);
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }

    /* --- KANBAN CARDS (Design Glass/Transparente) --- */
    .k-column-header {
        font-size: 12px; font-weight: 800; text-transform: uppercase;
        color: var(--text-color); opacity: 0.7;
        border-bottom: 2px solid rgba(128, 128, 128, 0.3); 
        padding-bottom: 8px; margin-bottom: 20px; letter-spacing: 1px;
    }
    
    .kanban-card {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 10px; padding: 14px; margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.2s ease-in-out;
        color: var(--text-color);
    }
    
    .kanban-card:hover {
        transform: translateY(-3px); 
        box-shadow: 0 5px 10px rgba(0,0,0,0.1);
        border-color: #FF4B4B;
    }

    .k-card-header {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 10px; padding-bottom: 8px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.1);
    }
    
    .k-id { font-weight: 800; font-size: 14px; color: var(--text-color); }
    
    .k-fiscal-badge {
        font-size: 10px; padding: 3px 8px; border-radius: 12px;
        font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
    }

    .k-body { font-size: 13px; opacity: 0.9; margin-bottom: 8px; }
    .k-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
    .k-icon { opacity: 0.7; width: 16px; text-align: center; }

    /* Rota Box - Estilo sutil */
    .k-rota-box {
        background-color: rgba(128, 128, 128, 0.1); /* Transparente adaptativo */
        border-radius: 6px; padding: 8px; margin-top: 10px;
        font-size: 11px; border: 1px solid rgba(128, 128, 128, 0.1);
    }
    .k-rota-title { font-weight: 700; color: #29B5E8; margin-bottom: 4px; display: flex; align-items: center; gap: 5px;}
    .k-rota-flow { display: flex; align-items: center; gap: 6px; color: var(--text-color); opacity: 0.8; }
    
    .k-time { 
        font-size: 11px; color: var(--text-color); opacity: 0.5; 
        margin-top: 10px; text-align: right; font-style: italic; display: flex; justify-content: flex-end; align-items: center; gap: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. PROTEÇÃO DE ACESSO
# ==============================================================================
if "logado" not in st.session_state or not st.session_state["logado"]:
    st.warning("Acesso não autorizado.")
    st.switch_page("app.py")

# ==============================================================================
# FUNÇÃO MODAL
# ==============================================================================
@st.dialog("Detalhes do Processo")
def modal_detalhes_completo(id_proc, row, usuario_ativo):
    st.markdown(f"### Processo: **{id_proc}**")
    
    st.caption("Status Atual")
    status_atual = row.get('STATUS', 'ABERTO')
    cor_st = "green" if status_atual == "CONCLUÍDO" else "blue" if status_atual == "EM TRÂNSITO" else "orange"
    st.markdown(f":{cor_st}[**{status_atual}**]")
    st.divider()
    
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

    st.divider()
    st.markdown("#### Logística")
    col_mot, col_veic = st.columns(2)
    col_mot.text_input("Motorista", value=str(row.get('MOTORISTA', '')), disabled=True)
    col_veic.text_input("Veículo/Placa", value=str(row.get('VEICULO', '')), disabled=True)
    
    st.write("")
    st.markdown(f"**Rota:** `{row.get('LOCAL_ATUAL', 'Origem')}` ➝ `{row.get('LOCAL_DESTINO', 'Destino')}`")

    st.divider()
    st_fiscal = row.get('STATUS_FISCAL', 'PENDENTE')
    icone_fiscal = "✅" if "APROVADO" in st_fiscal else "⚠️" if "PENDENTE" in st_fiscal else "❌"
    st.markdown(f"**Status Fiscal:** {icone_fiscal} {st_fiscal}")
    
    st.write("")
    if st.button("Fechar", use_container_width=True):
        st.rerun()

# ==============================================================================
# 3. SIDEBAR
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
# 4. PREPARAÇÃO DE DADOS E KPIs
# ==============================================================================
df = carregar_dados("REGISTRO_DEVOLUCOES")

# Obter hora atual BRASIL
agora_br = datetime.now(FUSO_BR)

# Variáveis padrão
total_aberto = total_concluido = pendencia_fiscal = total_atrasados = 0
destinos_populares = "N/A"
itens_em_armazem = 0

if not df.empty:
    df.columns = df.columns.str.strip().str.upper()
    
    # Processamento de Datas com Fuso
    if 'DATA_CRIACAO' in df.columns:
        # Força conversão de erros para NaT e assume dia/mês/ano
        df['DATA_OBJ'] = pd.to_datetime(df['DATA_CRIACAO'], dayfirst=True, errors='coerce')
    
    # KPIs Básicos
    if 'STATUS' in df.columns:
        total_aberto = len(df[df['STATUS'] == 'ABERTO'])
        total_concluido = len(df[df['STATUS'] == 'CONCLUÍDO'])
        
        # Lógica de atraso (Comparando apenas datas para evitar confusão de horas)
        if 'DATA_OBJ' in df.columns:
            # Pega a data de hoje (sem hora)
            hoje_date = agora_br.date()
            # Pega a data do dataframe (sem hora)
            df['DATA_ONLY'] = df['DATA_OBJ'].dt.date
            
            # Filtro: Não concluído E (Hoje - DataCriação > 7 dias)
            mask_vencidos = (df['STATUS'] != 'CONCLUÍDO') & (df['DATA_ONLY'].apply(lambda x: (hoje_date - x).days if pd.notnull(x) else 0) > 7)
            total_atrasados = len(df[mask_vencidos])

    if 'STATUS_FISCAL' in df.columns:
        pendencia_fiscal = len(df[df['STATUS_FISCAL'].astype(str).str.contains('AGUARDANDO|PENDENTE', na=False)])
    
    # Métricas Page 5 (Estoque/Destino)
    if 'LOCAL_DESTINO' in df.columns:
        # Conta valores ignorando vazios
        contagem = df['LOCAL_DESTINO'].replace('', pd.NA).dropna().value_counts()
        destinos_populares = contagem.index[0] if not contagem.empty else "N/A"
    
    if 'LOCAL_ATUAL' in df.columns:
        itens_em_armazem = len(df[df['LOCAL_ATUAL'].astype(str).str.contains('CD|ARMAZEM|MATRIZ', case=False, na=False)])

# Saudação baseada na hora BR
hora = agora_br.hour
saudacao = "Bom dia" if 5 <= hora < 12 else "Boa tarde" if 12 <= hora < 18 else "Boa noite"
cargo_user = st.session_state.get('cargo', 'Colaborador')

# ==============================================================================
# 5. DASHBOARD LAYOUT
# ==============================================================================

# --- HEADER ---
st.markdown(f"""
<div class="welcome-container">
    <div class="welcome-text">
        <h2>{saudacao}, {usuario_nome}!</h2>
        <p>Painel de Controle Unificado - <strong>{cargo_user}</strong></p>
    </div>
    <div class="date-badge">📅 {agora_br.strftime('%d/%m/%Y')}</div>
</div>
""", unsafe_allow_html=True)

# --- KPIs ---
st.markdown("#### 📊 Métricas Chave")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📦 Fila (Aberto)", total_aberto, delta_color="off")
k2.metric("⚖️ Pend. Fiscal", pendencia_fiscal, delta="Atenção", delta_color="inverse")
k3.metric("🔥 Atrasados (>7d)", total_atrasados, delta="Crítico", delta_color="inverse")
k4.metric("🏢 No Armazém", itens_em_armazem)
k5.metric("📍 Top Destino", destinos_populares)

st.divider()

# ==============================================================================
# 6. KANBAN (HTML SEGURO E CORRIGIDO)
# ==============================================================================
if not df.empty and 'STATUS' in df.columns:
    st.subheader("📌 Fluxo de Processos")
    
    fluxo = ["ABERTO", "EM ANÁLISE", "EM TRÂNSITO", "CONCLUÍDO"]
    # Cores mais vibrantes para os headers das colunas
    cores_coluna = {"ABERTO": "#FF4B4B", "EM ANÁLISE": "#FFA726", "EM TRÂNSITO": "#29B5E8", "CONCLUÍDO": "#00C853"}
    
    cols = st.columns(4)
    
    for i, status in enumerate(fluxo):
        with cols[i]:
            # Renderiza Header da Coluna
            cor = cores_coluna[status]
            st.markdown(f"<div class='k-column-header' style='border-color: {cor}; color: {cor};'>{status}</div>", unsafe_allow_html=True)
            
            # Filtra e Ordena (Mais novos primeiro na visualização ou mais antigos? Geralmente Kanban é fila)
            # Vamos mostrar os últimos (tail) para não poluir, mas idealmente seria head (mais antigos) se for fila de trabalho.
            itens = df[df['STATUS'] == status]
            
            if itens.empty:
                st.markdown("<div style='text-align: center; opacity: 0.5; font-size: 12px; margin-top: 10px;'>— Vazio —</div>", unsafe_allow_html=True)
            
            # Iterar sobre os cards (limitando a 5 para performance visual)
            for _, row in itens.tail(5).iterrows():
                id_proc = row.get('ID_PROCESSO', '?')
                
                # --- PREPARAÇÃO DOS DADOS (PYTHON) ---
                st_fiscal = row.get('STATUS_FISCAL', 'PENDENTE')
                
                # Lógica de cores Fiscal (Adaptada para CSS Variables se possível, mas mantendo cores fixas para status é melhor para semântica)
                if "APROVADO" in st_fiscal:
                    bg_fisc, fg_fisc = "#e8f5e9", "#2e7d32" # Verde suave / Verde escuro
                elif "REJEITADO" in st_fiscal:
                    bg_fisc, fg_fisc = "#ffebee", "#c62828" # Vermelho suave / Vermelho escuro
                elif "AGUARDANDO" in st_fiscal:
                    bg_fisc, fg_fisc = "#fff3e0", "#ef6c00" # Laranja suave / Laranja escuro
                else:
                    bg_fisc, fg_fisc = "#f5f5f5", "#616161" # Cinza

                nf_val = row.get('NF', '-')
                resp_val = str(row.get('RESPONSAVEL', 'System')).split(' ')[0].title()
                
                veic = str(row.get('VEICULO', ''))
                mot = str(row.get('MOTORISTA', '')).split(' ')[0].title()
                
                # Tratamento de Strings vazias para evitar quebra HTML
                loc_atual = str(row.get('LOCAL_ATUAL', '')).strip()
                loc_dest = str(row.get('LOCAL_DESTINO', '')).strip()
                if not loc_atual: loc_atual = "Origem"
                if not loc_dest: loc_dest = "Destino"
                
                info_transporte = f"{veic} • {mot}" if (veic and mot) else mot if mot else "Sem motorista"
                
                # Cálculo de Tempo (Fuso Correto)
                dias_aberto = 0
                str_tempo = "Hoje"
                if 'DATA_OBJ' in df.columns and not pd.isna(row['DATA_OBJ']):
                     # Converte para data simples para comparar dias
                     data_proc = row['DATA_OBJ'].date()
                     hoje_date = agora_br.date()
                     dias_aberto = (hoje_date - data_proc).days
                     
                     if dias_aberto == 0: str_tempo = "Hoje"
                     elif dias_aberto == 1: str_tempo = "Ontem"
                     else: str_tempo = f"há {dias_aberto}d"
                
                icon_time = "🔥" if dias_aberto > 7 else "🕒"

                # --- MONTAGEM DO HTML (SEM F-STRING MULTILINHA PARA EVITAR ERRO) ---
                # Construímos as partes separadamente para garantir integridade
                
                div_rota = ""
                # Só mostra rota se houver locais definidos e não for placeholders
                if loc_atual not in ['...', ''] or loc_dest not in ['...', '']:
                    div_rota = (
                        f'<div class="k-rota-box">'
                        f'<div class="k-rota-title">🚛 {info_transporte}</div>'
                        f'<div class="k-rota-flow">'
                        f'<span>{loc_atual}</span> <span style="color:#FF4B4B; font-weight:bold;">➝</span> <span>{loc_dest}</span>'
                        f'</div></div>'
                    )

                html_card = (
                    f'<div class="kanban-card">'
                    f'  <div class="k-card-header">'
                    f'      <span class="k-id">{id_proc}</span>'
                    f'      <span class="k-fiscal-badge" style="background-color: {bg_fisc}; color: {fg_fisc}; border: 1px solid {fg_fisc}40;">{st_fiscal}</span>'
                    f'  </div>'
                    f'  <div class="k-body">'
                    f'      <div class="k-row"><span class="k-icon">📄</span><strong>{nf_val}</strong></div>'
                    f'      <div class="k-row"><span class="k-icon">👤</span><span>{resp_val}</span></div>'
                    f'      {div_rota}'
                    f'  </div>'
                    f'  <div class="k-time">{icon_time} {str_tempo}</div>'
                    f'</div>'
                )
                
                st.markdown(html_card, unsafe_allow_html=True)
                
                # --- BOTÕES DE AÇÃO (Layout 1 | 4 | 1) ---
                b_col1, b_col2, b_col3 = st.columns([1, 4, 1])
                
                # Voltar
                if i > 0:
                    if b_col1.button("◀", key=f"btn_prev_{id_proc}", help="Voltar fase"):
                        atualizar_status_devolucao(id_proc, fluxo[i-1])
                        st.rerun()

                # Detalhes (Botão Expandido)
                if b_col2.button("Detalhes", key=f"btn_det_{id_proc}", use_container_width=True):
                    try:
                        modal_detalhes_completo(id_proc, row, st.session_state.get('usuario', 'Anon'))
                    except:
                        st.switch_page("pages/3_📋_Gestao_Tratativas.py")

                # Avançar
                if i < len(fluxo) - 1:
                    if b_col3.button("▶", key=f"btn_next_{id_proc}", help="Avançar fase"):
                        atualizar_status_devolucao(id_proc, fluxo[i+1])
                        st.rerun()
                
                st.write("") # Espaçamento entre cards

else:
    st.info("Nenhum processo encontrado no momento.")