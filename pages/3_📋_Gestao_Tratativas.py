import streamlit as st
import pandas as pd
import uuid
import time
import re # Importante para limpar o texto da moeda
from datetime import datetime, date, timedelta
from pathlib import Path

# Proteção de acesso
if "logado" not in st.session_state or not st.session_state["logado"]:
    st.switch_page("app.py")

# ==============================================================================
# FUNÇÕES AUXILIARES MATEMÁTICAS - CORREÇÃO PRINCIPAL
# ==============================================================================
def card_html(label, value, border_class, sub_html=""):
    return f"""
    <div class="kpi-card {border_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """

def converter_br_para_float(valor):
    """
    Transforma strings sujas ('R$ 1.000,50') em float puro (1000.50).
    Evita a concatenação de texto.
    """
    if pd.isna(valor) or valor is None:
        return 0.0
    
    s = str(valor).strip()
    
    # Se já é vazio, retorna 0
    if s == "" or s.lower() == "nan" or s.lower() == "none":
        return 0.0
    
    # Remove R$, espaços
    s = re.sub(r'R\$', '', s)
    s = re.sub(r'\s+', '', s)
    
    # Remove pontos de milhar (1.000 -> 1000)
    s = re.sub(r'\.(?=\d{3})', '', s)
    
    # Troca vírgula decimal por ponto (50,00 -> 50.00)
    s = s.replace(',', '.')
    
    try:
        return float(s)
    except ValueError:
        # Se ainda falhar, tenta extrair apenas números e ponto
        numeros = re.findall(r'[\d.]+', s)
        if numeros:
            try:
                return float(numeros[0])
            except:
                return 0.0
        return 0.0

def formatar_moeda(valor):
    """Transforma float em string bonita (R$ 1.000,00)"""
    try:
        # PRIMEIRO converte para float
        val_float = converter_br_para_float(valor)
        # DEPOIS formata
        return f"R$ {val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def calcular_total_processo(id_proc):
    """
    Retorna o valor total somado (float) e a string formatada.
    """
    df_itens = carregar_itens_por_processo(id_proc)
    if df_itens.empty:
        return 0.0, "R$ 0,00"
    
    total = 0.0
    
    # Verifica qual coluna usar
    if "VALOR_TOTAL" in df_itens.columns:
        coluna_valor = "VALOR_TOTAL"
    elif "TOTAL" in df_itens.columns:
        coluna_valor = "TOTAL"
    elif "VALOR" in df_itens.columns:
        coluna_valor = "VALOR"
    else:
        # Tenta calcular QTD * VALOR_UNIT se disponível
        if "QTD" in df_itens.columns and "VALOR_UNIT" in df_itens.columns:
            df_itens["VALOR_CALCULADO"] = df_itens.apply(
                lambda row: converter_br_para_float(row.get("QTD", 0)) * 
                           converter_br_para_float(row.get("VALOR_UNIT", 0)), 
                axis=1
            )
            coluna_valor = "VALOR_CALCULADO"
        else:
            return 0.0, "R$ 0,00"
    
    # Aplica conversão e soma
    total = df_itens[coluna_valor].apply(converter_br_para_float).sum()
    
    # Formata o resultado
    total_fmt = f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    return total, total_fmt

# ==============================================================================
# CSS: ESTILOS VISUAIS (ATUALIZADO COM DESIGN DA PAGE 1)
# ==============================================================================
st.markdown("""
<style>
            /* --- CORREÇÃO DA SIDEBAR (FORÇAR TOPO) --- */
    /* Remove o padding padrão gigante do Streamlit no topo da sidebar */
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1rem !important; /* Reduzido de 6rem para 1rem */
        padding-bottom: 1rem !important;
    }
    
    /* Garante que o container ocupe a altura toda para o Flexbox funcionar */
    section[data-testid="stSidebar"] > div {
        height: 100vh;
    }
    
    /* Ajusta o conteúdo interno para começar do topo absoluto */
    div[data-testid="stSidebarUserContent"] {
        padding-top: 0rem !important;
        display: flex;
        flex-direction: column;
        height: 100%;
        justify-content: space-between; /* Separa Topo e Rodapé */
    }

    /* Reduz margem da imagem do logo */
    div[data-testid="stImage"] {
        margin-bottom: 20px;
    }

    /* Esconde Nav Nativa (Padrão) */
    [data-testid="stSidebarNav"] {display: none;}
    
    /* --- ESTILOS DOS CARDS (MANTIDOS) --- */
    /* ... (Mantenha o resto do CSS dos Cards e Kanban aqui) ... */
    /* --- ANIMAÇÃO DE ENTRADA --- */
    @keyframes slideUpFade {
        0% { opacity: 0; transform: translateY(15px) scale(0.98); }
        100% { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* Esconde Nav Nativa */
    [data-testid="stSidebarNav"] {display: none;}
    
    /* Ajustes Gerais Sidebar */
    section[data-testid="stSidebar"] > div {height: 100vh; display: flex; flex-direction: column; justify-content: space-between; padding-top: 0px !important; padding-bottom: 20px !important;}
    
    /* --- KPI CARDS (Mantidos da Page 3) --- */
    .kpi-card {
        background-color: transparent; border-radius: 8px; padding: 15px 20px;
        margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        border: 1px solid rgba(128, 128, 128, 0.2); height: 100px;
        display: flex; flex-direction: column; justify-content: center;
    }
    .kpi-label { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--text-color); opacity: 0.6; margin-bottom: 5px; }
    .kpi-value { font-size: 32px; font-weight: 800; color: var(--text-color); line-height: 1; }
    
    /* Bordas Laterais KPIs */
    .border-white  { border-left: 5px solid var(--text-color); }
    .border-red    { border-left: 5px solid #e74c3c; }
    .border-green  { border-left: 5px solid #2ecc71; }
    .border-orange { border-left: 5px solid #f39c12; } 

    /* --- NOVOS ESTILOS DO KANBAN (Trazidos da Page 1) --- */
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
        color: var(--text-color);
        /* Animação */
        animation: slideUpFade 0.4s ease-out forwards;
        transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
    }
    
    .kanban-card:hover {
        transform: translateY(-4px) scale(1.01); 
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        border-color: #FF4B4B;
        z-index: 1;
    }

    .k-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid rgba(128, 128, 128, 0.1); }
    .k-id { font-weight: 800; font-size: 14px; color: var(--text-color); }
    .k-fiscal-badge { font-size: 10px; padding: 3px 8px; border-radius: 12px; font-weight: 700; text-transform: uppercase; }
    .k-body { font-size: 13px; opacity: 0.9; margin-bottom: 8px; }
    .k-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
    .k-icon { opacity: 0.7; width: 16px; text-align: center; }

    /* Rota Box */
    .k-rota-box {
        background-color: rgba(128, 128, 128, 0.1);
        border-radius: 6px; padding: 8px; margin-top: 10px;
        font-size: 11px; border: 1px solid rgba(128, 128, 128, 0.1);
    }
    .k-rota-title { font-weight: 700; color: #29B5E8; margin-bottom: 4px; }
    .k-rota-flow { display: flex; align-items: center; gap: 6px; color: var(--text-color); opacity: 0.8; }
    .k-time { font-size: 11px; color: var(--text-color); opacity: 0.5; margin-top: 10px; text-align: right; font-style: italic; }
    
    /* Outros */
    .chat-meta { font-size: 0.75rem; opacity: 0.7; margin-bottom: 2px; }
    .badge-total { background-color: rgba(0, 200, 83, 0.1); color: #00C853; padding: 4px 10px; border-radius: 6px; border: 1px solid #00C853; font-weight: bold; font-size: 13px; }
    .btn-ghost { display: inline-flex; align-items: center; background-color: transparent !important; border: 1px solid #FF4B4B !important; color: #FF4B4B !important; padding: 4px 12px; border-radius: 4px; text-decoration: none; font-size: 14px; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# SIDEBAR
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

# Importa as funções do Backend
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


st.title("Gestão de Tratativas")

def calcular_prazo_alerta(data_inicio_str, status_atual, data_fim_str=None):
    try:
        if not data_inicio_str or str(data_inicio_str).strip() in ["", "None", "NaT"]:
            return "SEM DATA INÍCIO", "grey"
        
        dt_inicio = pd.to_datetime(data_inicio_str, dayfirst=True, errors='coerce').date()
        if pd.isna(dt_inicio): return "DATA INVÁLIDA", "grey"

        if status_atual == "CONCLUÍDO":
            if data_fim_str and str(data_fim_str).strip() not in ["", "None"]:
                dt_fim = pd.to_datetime(data_fim_str, dayfirst=True, errors='coerce').date()
            else:
                dt_fim = datetime.now().date()
            texto_extra = " (Finalizado)"
        else:
            dt_fim = datetime.now().date()
            texto_extra = ""

        dias_corridos = (dt_fim - dt_inicio).days
        
        if dias_corridos < 3: return f"FRESCO ({dias_corridos} dias){texto_extra}", "#00B17C"
        elif dias_corridos < 5: return f"ATENÇÃO ({dias_corridos} dias){texto_extra}", "#5173C2"
        elif dias_corridos < 10: return f"PRAZO 10 ({dias_corridos} dias){texto_extra}", "#EC9E55"
        elif dias_corridos < 20: return f"PRAZO 20 ({dias_corridos} dias){texto_extra}", "#E9EB7B"
        else: return f"ESTOUROU ({dias_corridos} dias){texto_extra}", "#FF4B4B"
    except:
        return f"ERRO CÁLCULO", "grey"

def renderizar_chat_visual(df_msgs):
    if df_msgs.empty:
        st.caption("💬 Nenhum comentário ainda.")
        return

    for _, msg in df_msgs.iterrows():
        is_me = msg.get('USUARIO') == st.session_state.get('usuario')
        nome_user = msg.get('USUARIO', 'Desconhecido')
        hora = pd.to_datetime(msg.get('DATA_HORA')).strftime("%d/%m %H:%M")
        texto = msg.get('MENSAGEM', '')
        anexo = str(msg.get('ANEXO', ''))

        with st.chat_message("user" if is_me else "assistant"):
            st.markdown(f"<div class='chat-meta'><span class='chat-user'>{nome_user}</span> • {hora}</div>", unsafe_allow_html=True)
            if texto: st.write(texto)
            if anexo and anexo.startswith("http"):
                ext = anexo.split('.')[-1].lower()
                if ext in ['png', 'jpg', 'jpeg', 'gif']:
                    st.image(anexo, width=200)
                else:
                    st.markdown(f"[Abrir Documento ({ext})]({anexo})")

def limpar_cache(id_proc):
    if id_proc in st.session_state.anexo_cache: del st.session_state.anexo_cache[id_proc]
    st.session_state.reset_uploader += 1

if 'anexo_cache' not in st.session_state: st.session_state.anexo_cache = {} 
if 'reset_uploader' not in st.session_state: st.session_state.reset_uploader = 0 

# --- MODAL DETALHES (CORRIGIDO E LIMPO) ---
@st.dialog("Detalhes do Processo", width="large")
def modal_detalhes_completo(id_proc, dados_row, usuario_atual):
    # 1. Cabeçalho NFD
    link_nfd = dados_row.get('LINK_NFD', '')
    if link_nfd and str(link_nfd).startswith('http'):
        st.info(f"**Documento NFD Disponível:** [Clique para Visualizar]({link_nfd})")
    
    # 2. Dados Chave
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**ID:** `{id_proc}`")
    c2.markdown(f"**NF:** `{dados_row.get('NF', '-')}`")
    c3.markdown(f"**Resp:** {dados_row.get('RESPONSAVEL', '-')}")
    st.divider()
    
    # 3. TABELA DE ITENS COM TOTAL (CORRIGIDA)
    _, total_fmt = calcular_total_processo(id_proc)
    
    c_tit, c_tot = st.columns([1, 1])
    c_tit.caption("Itens da Devolução")
    c_tot.markdown(f"""
        <div style="text-align: right;">
            <span class="badge-total">Total: {total_fmt}</span>
        </div>
    """, unsafe_allow_html=True)
    
    df_itens = carregar_itens_por_processo(id_proc)
    if not df_itens.empty:
        df_show = df_itens.copy()
        
        # Formata Visualmente para a Tabela
        if "VALOR_UNIT" in df_show.columns: 
            df_show["VALOR_UNIT"] = df_show["VALOR_UNIT"].apply(formatar_moeda)
        if "VALOR_TOTAL" in df_show.columns: 
            df_show["VALOR_TOTAL"] = df_show["VALOR_TOTAL"].apply(formatar_moeda)
        
        cols_show = [c for c in ["COD_ITEM", "DESCRICAO", "QTD", "VALOR_UNIT", "VALOR_TOTAL"] if c in df_show.columns]
        st.dataframe(df_show[cols_show], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum item registrado.")
        
    st.divider()
    
    # 4. Chat
    st.caption("Histórico & Evidências")
    with st.container(height=400):
        df_msgs = carregar_mensagens(id_proc)
        renderizar_chat_visual(df_msgs)
        
    texto = st.chat_input("Adicionar observação...", key=f"modal_input_{id_proc}")
    if texto:
        salvar_mensagem(id_proc, usuario_atual, texto, "")
        st.rerun()

# --- CARREGAR DADOS ---
df_proc = carregar_dados("REGISTRO_DEVOLUCOES")

if not df_proc.empty:
    # Padroniza colunas para maiúsculo e sem espaços
    df_proc.columns = df_proc.columns.str.strip().str.upper()
    
    # === BLINDAGEM CONTRA ERRO DE COLUNA ===
    # Verifica se STATUS existe. Se não existir, cria com valor padrão "ABERTO"
    if "STATUS" not in df_proc.columns:
        # Tenta procurar alguma coluna que contenha "SITUACAO" ou "ESTADO" caso tenha renomeado
        st.warning("⚠️ Coluna 'STATUS' não encontrada na planilha. Usando padrão 'ABERTO' para evitar erro.")
        df_proc["STATUS"] = "ABERTO"
    
    # Verifica STATUS_FISCAL
    if "STATUS_FISCAL" in df_proc.columns: 
        # Preenche vazios, converte para texto, joga para MAIÚSCULO e remove espaços
        df_proc['STATUS_FISCAL'] = df_proc['STATUS_FISCAL'].fillna("PENDENTE").astype(str).str.upper().str.strip()
    else:
        df_proc['STATUS_FISCAL'] = "PENDENTE"
        
    # Verifica TIPO_CARGA (Nova coluna) - Garante que exista para não dar erro futuro
    if "TIPO_CARGA" not in df_proc.columns:
        df_proc["TIPO_CARGA"] = "DIRETA"
    # =======================================

    # Conversão de Data
    df_proc['DATA_OBJ'] = pd.to_datetime(
        df_proc['DATA_CRIACAO'], 
        format='mixed', 
        dayfirst=True, 
        errors='coerce'
    )

# --- FILTROS ---
hoje = datetime.now().date()
inicio_padrao = hoje - timedelta(days=30)
with st.expander("📅 Filtros & Visualização", expanded=True):
    c_check, c_d1, c_d2, c_view = st.columns([1, 1, 1, 2])
    usar_filtro_data = c_check.checkbox("Filtrar Período", value=True)
    data_inicio = c_d1.date_input("De:", value=inicio_padrao, disabled=not usar_filtro_data)
    data_fim = c_d2.date_input("Até:", value=hoje, disabled=not usar_filtro_data)
    tipo_visualizacao = c_view.radio("Visualização:", ["Lista", "Kanban"], horizontal=True, label_visibility="collapsed")

if not df_proc.empty:
    df_filtered = df_proc.copy()
    if usar_filtro_data:
        mask_data = (df_filtered['DATA_OBJ'].dt.date >= data_inicio) & (df_filtered['DATA_OBJ'].dt.date <= data_fim) & (df_filtered['DATA_OBJ'].notnull())
        df_filtered = df_filtered[mask_data]
else:
    df_filtered = pd.DataFrame()

st.divider()

total = len(df_filtered)
abertos = len(df_filtered[df_filtered['STATUS'] == 'ABERTO'])
concluidos = len(df_filtered[df_filtered['STATUS'] == 'CONCLUÍDO'])
# Correção do Fiscal aqui:
pend_fisc = len(df_filtered[df_filtered['STATUS_FISCAL'].astype(str).str.upper().str.contains('PENDENTE|AGUARDANDO|EM ANÁLISE', regex=True, na=False)])

# Renderização dos Cards
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(card_html("Total de Processos", f"{total}", "border-white"), unsafe_allow_html=True)

with c2:
    st.markdown(card_html("Em Aberto", f"{abertos}", "border-red"), unsafe_allow_html=True)

with c3:
    st.markdown(card_html("Concluídos", f"{concluidos}", "border-green"), unsafe_allow_html=True)

with c4:
    st.markdown(card_html("Pend. Fiscal", f"{pend_fisc}", "border-orange"), unsafe_allow_html=True)

st.write("")

# --- BUSCA ---
if not df_filtered.empty:
    col_f1, col_f2, col_f3 = st.columns(3)
    filtro_status = col_f1.multiselect("Status Logístico", options=df_filtered["STATUS"].unique())
    # Mudei o label para refletir que busca TUDO
    filtro_nf = col_f2.text_input("Buscar Geral (NF, OC, Motorista, ID...)") 
    filtro_statusfiscal = col_f3.multiselect("Status Fiscal", options=df_filtered["STATUS_FISCAL"].unique())

    df_view = df_filtered.copy()
    
    # Filtros exatos (Dropdowns)
    if filtro_status: 
        df_view = df_view[df_view["STATUS"].isin(filtro_status)]
    
    if filtro_statusfiscal: 
        df_view = df_view[df_view["STATUS_FISCAL"].isin(filtro_statusfiscal)]
    
    # Busca Textual Global
    if filtro_nf:
        termo = filtro_nf.upper().strip()
        # Verifica se o termo existe em QUALQUER coluna da linha
        mask = df_view.astype(str).apply(lambda x: x.str.upper().str.contains(termo, na=False)).any(axis=1)
        df_view = df_view[mask]
        
else:
    df_view = pd.DataFrame()

# =================================================================================
# MODO LISTA (PRINCIPAL)
# =================================================================================
if tipo_visualizacao == "Lista":
    st.caption(f"📋 {len(df_view)} registros encontrados.")
    
    if df_view.empty:
        st.info("Nenhum processo encontrado com os filtros aplicados.")
    
    for index, row in df_view.iterrows():
        id_proc = row['ID_PROCESSO']
        status_log = row.get('STATUS', 'ABERTO')
        status_fisc = row.get('STATUS_FISCAL', 'PENDENTE')
        
        # Badges
        if status_log == "ABERTO": badge_log = ":red-background[ABERTO]"
        elif status_log == "CONCLUÍDO": badge_log = ":green-background[CONCLUÍDO]"
        else: badge_log = f":orange-background[{status_log}]"
        
        if status_fisc == "APROVADO": badge_fisc = ":green[APROVADO]"
        elif status_fisc == "REJEITADO": badge_fisc = ":red[REJEITADO]"
        elif "PENDENTE" in status_fisc: badge_fisc = ":orange[PENDENTE]"
        else: badge_fisc = f":grey[{status_fisc}]"

        # ✅ CÁLCULO TOTAL CORRETO
        _, valor_total_str = calcular_total_processo(id_proc)

        motivo_curto = str(row.get('MOTIVO', ''))[:60]
        
        # TÍTULO COM O VALOR TOTAL
        titulo_card = f"{badge_log} **{id_proc}** | NF: {row.get('NF', '?')} | {valor_total_str} | {motivo_curto}..."
        
        with st.expander(titulo_card):
            link_nfd = row.get('LINK_NFD', '')
            if link_nfd and str(link_nfd).startswith("http"):
                df_itens = carregar_itens_por_processo(id_proc)
                numero_nfd = "N/A"
                if not df_itens.empty and "NUMERO_NFD" in df_itens.columns:
                    numero_nfd = df_itens["NUMERO_NFD"].iloc[0]
                    if pd.isna(numero_nfd) or str(numero_nfd).strip() == "": numero_nfd = "N/A"
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                    <div style="color: white; font-weight: 600; font-size: 14px;">📄 Nota Fiscal de Devolução (NFD): {numero_nfd}</div>
                    <a href="{link_nfd}" target="_blank" class="btn-ghost" style="border-color: white !important; color: white !important;">Abrir Documento</a>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f"**Fiscal:** {badge_fisc} &nbsp; | &nbsp; **Ordem de Carga:** {row.get('ORDEM_DE_CARGA','-')} &nbsp; | &nbsp; **Origem:** {row.get('LOCAL','-')} &nbsp; | &nbsp; **Data:** {row.get('DATA_CRIACAO', '-')}")
            st.caption(f"Responsável: {row.get('RESPONSAVEL','-')} | OC: {row.get('OC','-')} | TIPO VEÍCULO: {row.get('TIPO_VEICULO','-')} | TIPO CARGA: {row.get('TIPO_CARGA','-')}")
            st.divider()

            # TABELA NO EXPANDER
            df_itens = carregar_itens_por_processo(id_proc)
            if not df_itens.empty:
                st.markdown(f"**Itens do Processo** (Total: {valor_total_str})")
                df_show = df_itens.copy()
                if "VALOR_TOTAL" in df_show.columns: 
                    df_show["VALOR_TOTAL"] = df_show["VALOR_TOTAL"].apply(formatar_moeda)
                if "VALOR_UNIT" in df_show.columns:
                    df_show["VALOR_UNIT"] = df_show["VALOR_UNIT"].apply(formatar_moeda)
                    
                cols_show = [c for c in ["COD_ITEM", "DESCRICAO", "QTD", "VALOR_UNIT", "VALOR_TOTAL"] if c in df_show.columns]
                st.dataframe(df_show[cols_show], use_container_width=True, hide_index=True)
            
            st.write("")
            col_l, col_r = st.columns([1.1, 1])
            
            # --- ÁREA DE EDIÇÃO ---
            with col_l:
                st.markdown("#### Tratativa & Transporte")
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

                    st.markdown("---")
                    c_dados, c_anexo = st.columns([1, 1.5]) 
                    with c_dados:
                        dt_base = str(row.get('DATA_DEVOLUCAO_CTE', '') or row.get('DATA_EMISSAO', ''))
                        st_atual = str(row.get('STATUS', 'ABERTO'))
                        dt_final = str(row.get('DATA_FIM', '')) 
                        msg_prazo, cor_prazo = calcular_prazo_alerta(dt_base, st_atual, dt_final)
                        
                        st.markdown(f"""<div style="margin-top: 5px; margin-bottom: 15px; padding: 8px; border-radius: 4px; background-color: {cor_prazo}20; border-left: 4px solid {cor_prazo}; color: {cor_prazo}; font-weight: bold; font-size: 13px;">⏱️ {msg_prazo} <br><span style="font-size:10px; color:#888">Início: {dt_base}</span></div>""", unsafe_allow_html=True)

                        val_cte_atual = str(row.get("COD_CTE",""))
                        if val_cte_atual == "None": val_cte_atual = ""
                        n_cod_cte = st.text_input("Cód. CTE", value=val_cte_atual)

                        data_str = str(row.get("DATA_DEVOLUCAO_CTE",""))
                        val_data_inicial = None 
                        if data_str and data_str not in ["None", "", "NaT"]:
                            try: val_data_inicial = pd.to_datetime(data_str, dayfirst=True).date()
                            except: val_data_inicial = None
                        n_data_dev = st.date_input("Data Devolução", value=val_data_inicial, format="DD/MM/YYYY")
                        
                    with c_anexo:
                        arqcte_status = st.file_uploader("PDF do CTE", key=f"up_cte_{id_proc}", type=["pdf", "png", "jpg"])
                        link_anexo_atual_cte = str(row.get("CTE_ANEXO",""))
                        if link_anexo_atual_cte and link_anexo_atual_cte.startswith("http"):
                            st.caption(f"📎 Atual: [Ver Arquivo]({link_anexo_atual_cte})")

                    st.markdown("---")
                    c_cob1, c_cob2 = st.columns([1, 1.5])
                    with c_cob1:

                        val_cob_atual = str(row.get('COD_COB', ''))
                        if val_cob_atual.lower() in ["nan", "none", "nat"]:
                            val_cob_atual = ""
                        if val_cob_atual.endswith('.0'):
                            val_cob_atual = val_cob_atual[:-2]

                        n_cod_cob = c_cob1.text_input("Cód. Ocorrência", value=val_cob_atual)
                        data_str_cob = str(row.get("COB_DATA",""))
                        val_data_cob = None
                        if data_str_cob and data_str_cob not in ["None", "", "NaT"]:
                            try: val_data_cob = pd.to_datetime(data_str_cob).date()
                            except: val_data_cob = None
                        n_data_cob = st.date_input("Data Emissão COB", value=val_data_cob, format="DD/MM/YYYY")
                                
                    with c_cob2:
                        arq_status = c_cob2.file_uploader("Evidência COB", key=f"up_cob_{id_proc}", type=["pdf", "png", "jpg"])
                        link_anexo_atual = str(row.get('COB_ANEXO', ''))
                        if link_anexo_atual and link_anexo_atual.startswith('http'):
                            st.caption(f"COB Anexada: [Ver Arquivo]({link_anexo_atual})")
                        st.write("")
                    
                    val_ordem_carga = str(row.get('ORDEM_DE_CARGA', '') or row.get('ORDEM_CARREGAMENTO', '') or '')

                    if st.form_submit_button("💾 Salvar Tudo", type="primary"):
                        with st.spinner("Processando..."):
                            link_final_cte = ""
                            if arqcte_status:
                                link_final_cte = upload_bytes_cloudinary(arqcte_status.getvalue(), f"CTE_{id_proc}_{arqcte_status.name}")
                                salvar_mensagem(id_proc, st.session_state.get('usuario', 'System'), f"📎 Novo CTE anexado.", link_final_cte)
                            
                            link_final_cob = ""
                            if arq_status:
                                link_final_cob = upload_bytes_cloudinary(arq_status.getvalue(), f"COB_{id_proc}_{arq_status.name}")
                                salvar_mensagem(id_proc, st.session_state.get('usuario', 'System'), f"📎 Nova evidência anexada.", link_final_cob)
                            
                            sucesso = atualizar_tratativa_completa(
                                id_proc, n_log, n_fisc, n_cod_cob, 
                                link_final_cob, link_final_cte, n_cod_cte,
                                n_veiculo, n_motorista, n_loc_atual, n_loc_dest,
                                n_oc, n_data_dev, n_data_cob, val_ordem_carga
                            )

                            if sucesso:
                                st.success("✅ Atualizado com sucesso!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Erro ao salvar na planilha.")
            
            # --- CHAT (DIREITA) ---
            with col_r:
                head_c1, head_c2 = st.columns([3, 1])
                head_c1.markdown("#### Histórico")
                if head_c2.button("⤢", key=f"full_{id_proc}", help="Detalhes"):
                    modal_detalhes_completo(id_proc, row, st.session_state.get('usuario', 'Anon'))

                cont_chat = st.container(height=500, border=True)
                df_msgs = carregar_mensagens(id_proc)
                with cont_chat:
                    renderizar_chat_visual(df_msgs)

                with st.container():
                    c_anexo, c_input, c_btn = st.columns([0.15, 0.70, 0.15])
                    with c_anexo:
                        with st.popover("📎", use_container_width=True):
                            key_up = f"up_{id_proc}_{st.session_state.reset_uploader}"
                            file_up = st.file_uploader("", type=["pdf", "png", "jpg"], key=key_up)
                            if file_up:
                                st.session_state.anexo_cache[id_proc] = {'bytes': file_up.getvalue(), 'nome': file_up.name}
                            if id_proc in st.session_state.anexo_cache:
                                st.success("!")
                                if st.button("x", key=f"cls_{id_proc}"): limpar_cache(id_proc); st.rerun()

                    with st.form(key=f"form_chat_{id_proc}", clear_on_submit=True):
                        c_in, c_send = st.columns([5, 1])
                        texto_msg = c_in.text_input("Msg", placeholder="Digite...", label_visibility="collapsed")
                        enviou = c_send.form_submit_button("➤", use_container_width=True)
                        if enviou and texto_msg:
                            link_final = ""
                            if id_proc in st.session_state.anexo_cache:
                                dados = st.session_state.anexo_cache[id_proc]
                                link_final = upload_bytes_cloudinary(dados['bytes'], f"CHAT_{id_proc}_{dados['nome']}")
                                limpar_cache(id_proc)
                            salvar_mensagem(id_proc, st.session_state.get('usuario','Anon'), texto_msg, link_final)
                            st.rerun()
                st.divider()
                col_msg, col_btn = st.columns([3, 1])
                with col_msg: st.caption(f"Zona de Perigo: A exclusão do ID **{id_proc}** é irreversível.")
                with col_btn:
                    with st.popover("🗑️", use_container_width=True):
                        st.markdown(f"Tem certeza que deseja apagar o processo **{id_proc}**?")
                        if st.button("Confirmar Exclusão", type="primary", key=f"btn_del_{id_proc}"):
                            with st.spinner("Excluindo registros..."):
                                if excluir_processo_completo(id_proc):
                                    st.success("Processo excluído com sucesso!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Erro ao excluir.")

# =================================================================================
# MODO KANBAN (VISUAL PAGE 1 - DADOS PAGE 3)
# =================================================================================
elif tipo_visualizacao == "Kanban":
    st.write("") # Espaçamento superior
    
    fluxo = ["ABERTO", "EM ANÁLISE", "EM TRÂNSITO", "CONCLUÍDO"]
    # Cores vibrantes para os headers
    cores_coluna = {"ABERTO": "#FF4B4B", "EM ANÁLISE": "#FFA726", "EM TRÂNSITO": "#29B5E8", "CONCLUÍDO": "#00C853"}
    
    cols = st.columns(4)
    
    for i, status in enumerate(fluxo):
        with cols[i]:
            # --- HEADER DA COLUNA ---
            cor = cores_coluna[status]
            st.markdown(f"<div class='k-column-header' style='border-color: {cor}; color: {cor};'>{status}</div>", unsafe_allow_html=True)
            
            # Filtra itens usando df_view (os dados filtrados da Page 3)
            itens = df_view[df_view['STATUS'] == status]
            
            if itens.empty: 
                st.markdown("<div style='text-align: center; opacity: 0.5; font-size: 12px; margin-top: 10px;'>— Vazio —</div>", unsafe_allow_html=True)
            
            # --- LOOP DOS CARDS ---
            for _, row in itens.iterrows():
                id_proc = row['ID_PROCESSO']
                
                # 1. Preparação de Dados
                st_fiscal = row.get('STATUS_FISCAL', 'PENDENTE')
                
                # Cores Fiscal (Lógica do CSS novo)
                bg_fisc, fg_fisc = "#f5f5f5", "#616161" # Default
                if "APROVADO" in st_fiscal: bg_fisc, fg_fisc = "#e8f5e9", "#2e7d32"
                elif "REJEITADO" in st_fiscal: bg_fisc, fg_fisc = "#ffebee", "#c62828"
                elif "AGUARDANDO" in st_fiscal or "PENDENTE" in st_fiscal: bg_fisc, fg_fisc = "#fff3e0", "#ef6c00"

                nf_val = row.get('NF', '-')
                resp_val = str(row.get('RESPONSAVEL', 'System')).split(' ')[0].title()
                
                veic = str(row.get('VEICULO', '') or '?')
                mot = str(row.get('MOTORISTA', '') or '?').split(' ')[0].title()
                
                loc_atual = str(row.get('LOCAL_ATUAL', '...'))
                loc_dest = str(row.get('LOCAL_DESTINO', 'Destino'))
                
                info_transporte = f"{veic} • {mot}" if (veic != '?' and mot != '?') else mot if mot != '?' else "Transp. N/D"

                # 2. HTML da Rota (Sintaxe segura para evitar quebra)
                div_rota = ""
                # Só exibe se tiver informação relevante
                if loc_atual not in ['...', '', 'None'] or loc_dest not in ['Destino', '', 'None']:
                    div_rota = (
                        f'<div class="k-rota-box">'
                        f'  <div class="k-rota-title">🚛 {info_transporte}</div>'
                        f'  <div class="k-rota-flow">'
                        f'      <span>{loc_atual}</span>' 
                        f'      <span style="color:#FF4B4B; font-weight:bold;">➝</span>' 
                        f'      <span>{loc_dest}</span>'
                        f'  </div>'
                        f'</div>'
                    )

                # 3. HTML DO CARD (Estrutura Page 1)
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
                    f'  <div class="k-time" style="margin-top:5px;">📅 {row.get("DATA_CRIACAO", "")}</div>'
                    f'</div>'
                )
                
                # Renderiza Card
                st.markdown(html_card, unsafe_allow_html=True)
                
                # 4. BOTÕES (Lógica Page 3 mantida: Detalhes abre Modal)
                b1, b2, b3 = st.columns([1, 4, 1])
                
                # Botão Voltar
                if i > 0:
                    if b1.button("◀", key=f"p3_prev_{id_proc}", help=f"Voltar para {fluxo[i-1]}"):
                        atualizar_status_devolucao(id_proc, fluxo[i-1])
                        st.rerun()
                
                # Botão Detalhes (Abre o Modal específico da Page 3)
                if b2.button("Detalhes", key=f"p3_det_{id_proc}", use_container_width=True):
                    modal_detalhes_completo(id_proc, row, st.session_state.get('usuario', 'Anon'))
                
                # Botão Avançar
                if i < len(fluxo) - 1:
                    if b3.button("▶", key=f"p3_next_{id_proc}", help=f"Avançar para {fluxo[i+1]}"):
                        atualizar_status_devolucao(id_proc, fluxo[i+1])
                        st.rerun()
                
                st.write("") # Espaço entre cards
