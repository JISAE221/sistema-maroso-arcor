import streamlit as st
import pandas as pd
import time
import pytz # Essencial para corrigir o horário
from datetime import datetime
from services.conexao_sheets import carregar_dados, atualizar_status_devolucao

# ==============================================================================
# 1. CONFIGURAÇÃO E FUSO HORÁRIO
# ==============================================================================
st.set_page_config(page_title="Dashboard - Maroso", page_icon="📊", layout="wide")

# Define Fuso Horário de SP
FUSO_BR = pytz.timezone('America/Sao_Paulo')

# ==============================================================================
# 2. CSS AVANÇADO (CARDS KPI CUSTOMIZADOS)
# ==============================================================================
st.markdown("""
<style>
    /* --- SIDEBAR --- */
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"] > div {
        height: 100vh; display: flex; flex-direction: column; justify-content: space-between;
        padding-bottom: 20px !important;
    }

    /* --- ANIMAÇÃO GERAL --- */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* --- HEADER DE BOAS VINDAS --- */
    .welcome-container {
        background-color: var(--secondary-background-color);
        padding: 24px 30px; border-radius: 12px;
        border-left: 6px solid #FF4B4B; /* Cor da marca */
        margin-bottom: 30px; 
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        animation: fadeIn 0.5s ease-out;
    }
    .welcome-text h2 { margin: 0; font-size: 26px; font-weight: 700; color: var(--text-color); }
    .welcome-text p { margin: 5px 0 0 0; font-size: 14px; opacity: 0.8; }
    .date-badge {
        background: rgba(255, 75, 75, 0.1); 
        color: #FF4B4B;
        padding: 8px 16px; border-radius: 20px;
        font-size: 13px; font-weight: 700;
        border: 1px solid rgba(255, 75, 75, 0.2);
    }

    /* --- KPI CARDS (CUSTOM HTML) --- */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(5, 1fr); /* 5 colunas iguais */
        gap: 15px;
        margin-bottom: 30px;
    }
    
    .kpi-card {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 10px;
        padding: 20px;
        display: flex; flex-direction: column; justify-content: space-between;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        transition: transform 0.2s, box-shadow 0.2s;
        animation: fadeIn 0.6s ease-out;
        min-height: 110px; /* Altura mínima uniforme */
    }
    
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        border-color: rgba(128, 128, 128, 0.3);
    }

    .kpi-title {
        font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;
        color: var(--text-color); opacity: 0.7; font-weight: 600;
        margin-bottom: 10px; display: flex; align-items: center; gap: 6px;
    }
    
    .kpi-value {
        font-size: 28px; font-weight: 800; color: var(--text-color);
        line-height: 1.1;
    }
    
    .kpi-footer {
        font-size: 11px; margin-top: 8px; font-weight: 500;
    }
    
    /* Cores de badge footer */
    .badge-alert { color: #e74c3c; background: rgba(231, 76, 60, 0.1); padding: 2px 6px; border-radius: 4px; }
    .badge-warn  { color: #f39c12; background: rgba(243, 156, 18, 0.1); padding: 2px 6px; border-radius: 4px; }
    .badge-ok    { color: #2ecc71; background: rgba(46, 204, 113, 0.1); padding: 2px 6px; border-radius: 4px; }
    .badge-info  { color: #3498db; background: rgba(52, 152, 219, 0.1); padding: 2px 6px; border-radius: 4px; }

    /* Estilo para telas menores */
    @media (max-width: 1200px) {
        .kpi-container { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 800px) {
        .kpi-container { grid-template-columns: repeat(2, 1fr); }
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. SIDEBAR E PROTEÇÃO
# ==============================================================================
if "logado" not in st.session_state or not st.session_state["logado"]:
    st.warning("Acesso não autorizado.")
    st.switch_page("app.py")

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
    
    st.markdown('<div style="margin-top:auto;"></div>', unsafe_allow_html=True)
    c_perfil, c_texto = st.columns([0.25, 0.75])
    with c_perfil: st.markdown("👤", unsafe_allow_html=True)
    with c_texto:
        usuario_nome = st.session_state.get('usuario', 'Admin').split(' ')[0].title()
        st.markdown(f"**{usuario_nome}**<br><span style='font-size:11px'>Logística</span>", unsafe_allow_html=True)
    if st.button("Sair"): st.session_state["logado"] = False; st.switch_page("app.py")

# ==============================================================================
# 4. PREPARAÇÃO DOS DADOS
# ==============================================================================
df = carregar_dados("REGISTRO_DEVOLUCOES")

# Variáveis padrão
total_aberto = total_concluido = pendencia_fiscal = total_atrasados = 0
destinos_populares = "—"
itens_em_armazem = 0

# Obtém data/hora correta (Brasil)
agora_br = datetime.now(FUSO_BR)

if not df.empty:
    df.columns = df.columns.str.strip().str.upper()
    
    # Processamento de Datas
    if 'DATA_CRIACAO' in df.columns:
        df['DATA_OBJ'] = pd.to_datetime(df['DATA_CRIACAO'], dayfirst=True, errors='coerce')
    
    # KPIs Básicos
    if 'STATUS' in df.columns:
        total_aberto = len(df[df['STATUS'] == 'ABERTO'])
        total_concluido = len(df[df['STATUS'] == 'CONCLUÍDO'])
        
        # Atraso (>7 dias)
        if 'DATA_OBJ' in df.columns:
            hoje_date = agora_br.date()
            # Garante que a conta de dias funcione mesmo com NaT
            mask_vencidos = (df['STATUS'] != 'CONCLUÍDO') & (df['DATA_OBJ'].apply(lambda x: (hoje_date - x.date()).days if pd.notnull(x) else 0) > 7)
            total_atrasados = len(df[mask_vencidos])

    if 'STATUS_FISCAL' in df.columns:
        pendencia_fiscal = len(df[df['STATUS_FISCAL'].astype(str).str.contains('AGUARDANDO|PENDENTE', na=False)])
    
    if 'LOCAL_DESTINO' in df.columns:
        contagem = df['LOCAL_DESTINO'].replace('', pd.NA).dropna().value_counts()
        if not contagem.empty:
            destinos_populares = contagem.index[0]
            # Truque UX: Se o nome for muito longo, pegamos a primeira palavra ou abreviamos
            if len(destinos_populares) > 15:
                destinos_populares = destinos_populares[:15] + "..."
    
    if 'LOCAL_ATUAL' in df.columns:
        itens_em_armazem = len(df[df['LOCAL_ATUAL'].astype(str).str.contains('CD|ARMAZEM|MATRIZ', case=False, na=False)])

# === LÓGICA DE SAUDAÇÃO CORRIGIDA ===
hora = agora_br.hour
if 5 <= hora < 12:
    saudacao = "Bom dia"
elif 12 <= hora < 18:
    saudacao = "Boa tarde"
else:
    saudacao = "Boa noite"

cargo_user = st.session_state.get('cargo', 'Analista de Dados')

# ==============================================================================
# 5. DASHBOARD UI (REFORMULADA)
# ==============================================================================

# --- HEADER (HTML CUSTOM) ---
st.markdown(f"""
<div class="welcome-container">
    <div class="welcome-text">
        <h2>{saudacao}, {usuario_nome}!</h2>
        <p>Painel de Controle Unificado &bull; <strong>{cargo_user}</strong></p>
    </div>
    <div class="date-badge">📅 {agora_br.strftime('%d/%m/%Y')}</div>
</div>
""", unsafe_allow_html=True)

# --- KPIs (AGORA USANDO HTML GRID PARA NÃO QUEBRAR O LAYOUT) ---
# Aqui eliminamos o st.metric e usamos nosso próprio HTML que respeita o CSS acima
st.markdown(f"""
<div class="kpi-container">
    <div class="kpi-card">
        <div class="kpi-title">📦 Fila (Aberto)</div>
        <div class="kpi-value">{total_aberto}</div>
        <div class="kpi-footer"><span class="badge-info">Aguardando</span></div>
    </div>
    
    <div class="kpi-card">
        <div class="kpi-title">⚖️ Pend. Fiscal</div>
        <div class="kpi-value">{pendencia_fiscal}</div>
        <div class="kpi-footer"><span class="badge-warn">Atenção Necessária</span></div>
    </div>
    
    <div class="kpi-card" style="border-left: 4px solid #e74c3c;">
        <div class="kpi-title">🔥 Atrasados (>7d)</div>
        <div class="kpi-value" style="color: #e74c3c;">{total_atrasados}</div>
        <div class="kpi-footer"><span class="badge-alert">Crítico</span></div>
    </div>
    
    <div class="kpi-card">
        <div class="kpi-title">🏢 No Armazém</div>
        <div class="kpi-value">{itens_em_armazem}</div>
        <div class="kpi-footer"><span class="badge-ok">Em Estoque</span></div>
    </div>
    
    <div class="kpi-card">
        <div class="kpi-title">📍 Top Destino</div>
        <div class="kpi-value" style="font-size: 20px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{destinos_populares}">
            {destinos_populares}
        </div>
        <div class="kpi-footer"><span class="badge-info">Mais frequente</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

st.write("") # Espaço respiro

# ... (DAQUI PARA BAIXO MANTÉM SEU KANBAN QUE JÁ CONSERTAMOS) ...
# Apenas adicionei um check para garantir que o código continue rodando
if 'df' in locals() and not df.empty:
    st.subheader("📌 Fluxo Recente")
    # ... (Seu código do Kanban vem aqui, igual ao anterior) ...
    # Se precisar que eu cole o código do Kanban aqui novamente, me avise,
    # mas o foco era o cabeçalho e os cards.