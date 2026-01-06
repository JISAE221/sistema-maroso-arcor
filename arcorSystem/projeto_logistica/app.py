import streamlit as st
import time
import os
from services.auth_service import autenticar_usuario

__version__ = "1.0.0"

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Maroso Transporte", 
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: COMPACTO E ELEGANTE ---
st.markdown("""
<style>
    /* 1. Limpeza da Interface */
    [data-testid="stSidebar"] {display: none;}
    section[data-testid="stSidebar"] {display: none;}
    
    /* 2. O CONTROLE DE TAMANHO */
    .block-container {
        max-width: 500px; /* Seu ajuste personalizado */
        padding-top: 8vh; 
        margin: 0 auto;
    }
    
    /* 3. Inputs mais discretos */
    .stTextInput input {
        font-size: 14px;
        padding: 8px;
        min-height: 0px;
    }
    
    /* 4. Títulos Controlados */
    .login-header {
        text-align: center;
        font-weight: 700;
        font-size: 20px;
        color: var(--text-color);
        margin-bottom: 5px;
    }
    .login-sub {
        text-align: center;
        font-size: 12px;
        color: var(--text-color);
        opacity: 0.6;
        margin-bottom: 25px;
    }
    
    /* 5. Rodapé pequeno */
    .footer-text {
        text-align: center;
        margin-top: 40px;
        font-size: 10px;
        opacity: 0.4;
    }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZAÇÃO ---
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if st.session_state["logado"]:
    st.switch_page("pages/1_📊_Dashboard.py")

# =========================================================
# LÓGICA DE LOGIN COMPACTA
# =========================================================

# 1. LOGO
col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
with col_img2:
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=280) # Seu ajuste de tamanho
    else:
        st.markdown("<h3 style='text-align: center; text-transform: uppercase;'>Maroso</h3>", unsafe_allow_html=True)

# 2. TÍTULOS
st.markdown('<div class="login-header">Acesso Restrito</div>', unsafe_allow_html=True)
st.markdown('<div class="login-sub">Gestão Logística</div>', unsafe_allow_html=True)

# 3. FORMULÁRIO COMPACTO
with st.form("login_form", clear_on_submit=False):
    usuario = st.text_input("Usuário", placeholder="Login").strip()
    senha = st.text_input("Senha", type="password", placeholder="••••••")
    
    st.write("") 
    
    submit = st.form_submit_button("ENTRAR", type="primary", use_container_width=True)
    
    if submit:
        if not usuario or not senha:
            st.warning("Preencha os campos.")
        else:
            with st.spinner("..."):
                sucesso, nome, cargo = autenticar_usuario(usuario, senha)
                
                if sucesso:
                    # --- A MÁGICA ACONTECE AQUI ---
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = nome
                    st.session_state['cargo'] = cargo
                    
                    # Mensagem de sucesso bonita (verde)
                    st.success(f"Bem-vindo(a), {nome}! 🚀")
                    
                    # Pausa de 1.5 segundos para ele ler a mensagem antes de mudar de página
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("Dados incorretos.")

# 4. RODAPÉ
st.markdown(f'<div class="footer-text">© 2026 Maroso Transportes v{__version__}</div>', unsafe_allow_html=True)