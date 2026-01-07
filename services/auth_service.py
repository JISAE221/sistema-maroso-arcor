import streamlit as st
import pandas as pd
import hashlib
from services.conexao_sheets import carregar_dados

def verificar_hash(senha_digitada, hash_armazenado):
    """
    Transforma a senha digitada em SHA-256 e compara com o banco.
    """
    try:
        # 1. Converte a senha digitada para bytes e gera o hash SHA-256
        senha_hash = hashlib.sha256(str(senha_digitada).encode('utf-8')).hexdigest()
        
        # 2. Compara (strip remove espaços em branco que podem ter vindo do CSV)
        return senha_hash == str(hash_armazenado).strip()
    except Exception as e:
        print(f"Erro no hash: {e}")
        return False

def autenticar_usuario(username, password):
    """
    Verifica login comparando HASHES e retorna (Sucesso, Nome, Cargo).
    """
    try:
        # 1. Busca dados (Via Requests/CSV - Rápido)
        df_users = carregar_dados("USUARIOS")
        
        if df_users.empty:
            return False, None, None

        # 2. Sanitização para evitar erros de tipo
        df_users['USERNAME'] = df_users['USERNAME'].astype(str)
        df_users['PASSWORD'] = df_users['PASSWORD'].astype(str)
        
        # 3. Filtra o usuário
        user_match = df_users[df_users['USERNAME'] == str(username)]
        
        if not user_match.empty:
            real_password = str(user_match.iloc[0]['PASSWORD']).strip()
            
            # Gera o hash do que foi digitado
            senha_digitada_hash = hashlib.sha256(str(password).encode('utf-8')).hexdigest()

            # --- DEBUG TEMPORÁRIO (O X9) ---
            st.write(f"Hash na Planilha: |{real_password}|")
            st.write(f"Hash Digitado...: |{senha_digitada_hash}|")
            # -------------------------------

            if senha_digitada_hash == real_password:

                hash_banco = user_match.iloc[0]['PASSWORD']
                
                # --- AQUI ESTAVA O PONTO CEGO ---
                # Antes: if str(password) == hash_banco: (Comparava texto com hash)
                # Agora: Usamos a função de verificação
                if verificar_hash(password, hash_banco):
                    # SUCESSO!
                    nome = user_match.iloc[0].get('NOME', username)
                    cargo = user_match.iloc[0].get('CARGO', 'Colaborador')
                    return True, nome, cargo
                else:
                    print(f"Falha de senha para {username}") # Log interno para debug
                    
            return False, None, None

    except Exception as e:
        st.error(f"Erro Auth: {e}")
        return False, None, None