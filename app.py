import streamlit as st
import pandas as pd
import requests
import time
import os
from services.auth_service import autenticar_usuario
from io import StringIO

@st.cache_data(ttl=600, show_spinner="Baixando dados do Google Sheets...")
def get_google_sheet_data(sheet_url):
    """
    Conecta ao Google Sheets fingindo ser um navegador, corrige encoding e retorna um DataFrame.
    """
    
    # Headers de "Spoofing" para parecer um browser real
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/csv,text/html,application/xhtml+xml,application/xml",
        "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7"
    }

    try:
        # 1. Requisição
        response = requests.get(sheet_url, headers=headers, timeout=10)
        response.raise_for_status() # Para tudo se der erro 400/500
        
        # 2. Correção de Encoding (O Pulo do Gato para o 'Logística')
        response.encoding = 'utf-8' 
        
        # 3. Verificação de Bloqueio (Safety Check)
        if "<!DOCTYPE html>" in response.text:
            st.error("🚨 O Google detectou o bot e retornou HTML em vez de CSV. Verifique os Headers.")
            return pd.DataFrame() # Retorna vazio para não quebrar o app
            
        # 4. Transformação em DataFrame
        df = pd.read_csv(StringIO(response.text))
        return df

    except requests.exceptions.RequestException as e:
        st.error(f"Erro de Conexão: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return pd.DataFrame()

# --- FIM DA FUNÇÃO ---

# Como você chama isso no seu app principal:
def check_password():
    """Retorna True se o login for bem sucedido"""

    def password_entered():
        """Callback quando o botão é clicado"""
        # 1. Pega o que o usuário digitou
        if "username" in st.session_state and "password" in st.session_state:
            user_input = st.session_state["username"]
            pass_input = st.session_state["password"]
        else:
            return # Se não tiver nada digitado, não faz nada

        # 2. Baixa a tabela de usuários usando a conexão via requests (RÁPIDA)
        try:
            # Pega o ID da planilha dos secrets
            id_planilha = st.secrets["ID_PLANILHA"]
            gid_usuarios = st.secrets["GID_PLANILHA"] # Ou o GID específico da aba de usuários se for diferente

            # Monta a URL
            url_usuarios = f"https://docs.google.com/spreadsheets/d/{id_planilha}/export?format=csv&gid={gid_usuarios}"
            
            # Busca os dados (vai usar o cache se já tiver baixado)
            df_users = get_google_sheet_data(url_usuarios)
            
            if df_users.empty:
                st.error("Erro: Não foi possível baixar a lista de usuários.")
                return

            # 3. Verifica se o usuário existe na tabela
            # Garante que a coluna de USERNAME seja string para comparação
            df_users['USERNAME'] = df_users['USERNAME'].astype(str)
            
            # Filtra onde a coluna USERNAME é igual ao que foi digitado
            user_match = df_users[df_users['USERNAME'] == user_input]
            
            if not user_match.empty:
                # Pega a senha correta (que está na planilha)
                real_password = str(user_match.iloc[0]['PASSWORD'])
                
                # Compara a senha digitada com a senha da planilha
                if pass_input == real_password:
                    st.session_state["password_correct"] = True
                    # Limpa as credenciais da memória por segurança
                    del st.session_state["password"]
                    del st.session_state["username"]
                else:
                    st.session_state["password_correct"] = False
            else:
                st.session_state["password_correct"] = False
                
        except Exception as e:
            st.error(f"Erro no processo de login: {e}")

    # --- Interface do Login ---
    if st.session_state.get("password_correct", False):
        return True

    # Se não estiver logado, mostra os campos de input
    st.markdown("### Acesso Restrito")
    
    st.text_input("Usuário", key="username")
    st.text_input("Senha", type="password", key="password")
    st.button("ENTRAR", on_click=password_entered)

    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("Usuário não encontrado ou senha incorreta.")
        
    return False

__version__ = "1.0.1"

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