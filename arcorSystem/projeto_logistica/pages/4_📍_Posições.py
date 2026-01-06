import streamlit as st
from pathlib import Path

# Proteção de acesso
if "logado" not in st.session_state or not st.session_state["logado"]:
    st.switch_page("app.py")

# ==============================================================================
# CSS: TRAVAR BARRA LATERAL (FULL HEIGHT)
# ==============================================================================
st.markdown("""
<style>
    /* 1. Oculta navegação padrão */
    [data-testid="stSidebarNav"] {display: none;}

    /* 2. Container Principal da Sidebar */
    section[data-testid="stSidebar"] > div {
        height: 100vh; /* Força altura total da viewport */
        display: flex;
        flex-direction: column;
        justify-content: space-between; /* Espalha: Topo vs Fundo */
        padding-top: 0px !important; /* Remove acolchoamento do Streamlit */
        padding-bottom: 20px !important;
    }

    /* 3. Ajuste do Bloco de Conteúdo Interno */
    /* Isso garante que o conteúdo comece do topo absoluto */
    div[data-testid="stSidebarUserContent"] {
        padding-top: 2rem !important; /* Pequeno respiro apenas */
        display: flex;
        flex-direction: column;
        height: 100%;
    }

    /* 4. Forçar a Logo a não ter margem extra */
    div[data-testid="stImage"] {
        margin-bottom: 20px;
    }
    
    /* 5. Estilo do Rodapé para garantir que fique lá embaixo */
    .footer-container {
        margin-top: auto; /* Empurra para o fundo se sobrar espaço */
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CONSTRUÇÃO DA SIDEBAR
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
        
    st.markdown('</div>', unsafe_allow_html=True) # Fecha footer-container