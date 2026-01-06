import pandas as pd
import hashlib
import streamlit as st
from services.conexao_sheets import get_worksheet

def make_hash(password):
    """Cria um hash SHA-256 da senha."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_password(password, hashed_password):
    """Verifica se a senha digitada bate com o hash salvo."""
    return make_hash(password) == hashed_password

def autenticar_usuario(username, password_input):
    """
    Busca o usuário na planilha e verifica a senha.
    Retorna: (Sucesso: bool, Nome: str, Cargo: str)
    """
    try:
        # Busca a aba USUARIOS
        ws = get_worksheet("USUARIOS")
        
        # Pega todos os registros (Cacheamos isso para não ler a cada clique)
        dados = ws.get_all_records()
        df_users = pd.DataFrame(dados)
        
        # Filtra pelo username (transforma em string para evitar erro de número)
        user_row = df_users[df_users['USERNAME'].astype(str) == username]
        
        if user_row.empty:
            return False, None, None
        
        # Pega a senha salva (hash)
        stored_hash = str(user_row.iloc[0]['PASSWORD'])
        nome = user_row.iloc[0]['NOME']
        cargo = user_row.iloc[0]['CARGO']
        
        # Verifica a senha
        if check_password(password_input, stored_hash):
            return True, nome, cargo
        else:
            return False, None, None
            
    except Exception as e:
        st.error(f"Erro na autenticação: {e}")
        return False, None, None