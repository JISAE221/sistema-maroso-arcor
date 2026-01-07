# services/auth_service.py
import streamlit as st
import pandas as pd
# Importamos a função de leitura rápida, não a antiga get_worksheet
from services.conexao_sheets import carregar_dados

def autenticar_usuario(username, password):
    """
    Verifica se o usuário e senha existem na aba USUARIOS.
    Retorna True se sucesso, False se falha.
    """
    try:
        # 1. Busca a tabela de usuários (RÁPIDO, via CSV)
        df_users = carregar_dados("USUARIOS")
        
        if df_users.empty:
            st.error("Erro: Base de usuários vazia ou inacessível.")
            return False

        # 2. Garante que as colunas sejam strings para evitar erro de comparação
        # Ajuste 'USERNAME' e 'PASSWORD' se na sua planilha os nomes forem diferentes (ex: 'Usuario', 'Senha')
        if 'USERNAME' not in df_users.columns or 'PASSWORD' not in df_users.columns:
            st.error("Erro: Colunas USERNAME/PASSWORD não encontradas na planilha.")
            return False
            
        df_users['USERNAME'] = df_users['USERNAME'].astype(str)
        df_users['PASSWORD'] = df_users['PASSWORD'].astype(str)

        # 3. Filtra o usuário
        user_match = df_users[df_users['USERNAME'] == str(username)]
        
        if not user_match.empty:
            # Pega a senha real da planilha
            real_password = user_match.iloc[0]['PASSWORD']
            
            # Compara (Aqui estamos comparando texto plano conforme seu csv anterior)
            # Se no futuro usar hash, mude a lógica aqui
            if str(password) == real_password:
                return True
                
        return False

    except Exception as e:
        st.error(f"Erro no serviço de autenticação: {e}")
        return False