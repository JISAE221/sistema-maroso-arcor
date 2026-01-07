import streamlit as st
import pandas as pd
from services.conexao_sheets import carregar_dados

def autenticar_usuario(username, password):
    """
    Verifica login e retorna (Sucesso, Nome, Cargo).
    """
    try:
        # 1. Busca dados
        df_users = carregar_dados("USUARIOS")
        
        if df_users.empty:
            return False, None, None

        # 2. Sanitização
        df_users['USERNAME'] = df_users['USERNAME'].astype(str)
        df_users['PASSWORD'] = df_users['PASSWORD'].astype(str)
        
        # 3. Filtro
        user_match = df_users[df_users['USERNAME'] == str(username)]
        
        if not user_match.empty:
            real_password = user_match.iloc[0]['PASSWORD']
            
            if str(password) == real_password:
                # SUCESSO: Pega os dados extras (Nome e Cargo)
                # O .get previne erro se a coluna não existir, retornando um padrão
                nome = user_match.iloc[0].get('NOME', username)
                cargo = user_match.iloc[0].get('CARGO', 'Colaborador')
                return True, nome, cargo
                
        return False, None, None

    except Exception as e:
        st.error(f"Erro Auth: {e}")
        return False, None, None