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
        
        # 2. Compara (strip remove espaços em branco/quebras de linha indesejados)
        # Convertemos ambos para string e minúsculas para garantir match exato
        return senha_hash.strip().lower() == str(hash_armazenado).strip().lower()
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
            st.error("Erro: Tabela de usuários não encontrada ou vazia.")
            return False, None, None

        # 2. Sanitização para evitar erros de tipo
        df_users['USERNAME'] = df_users['USERNAME'].astype(str)
        df_users['PASSWORD'] = df_users['PASSWORD'].astype(str)
        
        # 3. Filtra o usuário
        user_match = df_users[df_users['USERNAME'] == str(username)]
        
        if not user_match.empty:
            # Pega o hash que veio do Google Sheets
            hash_banco = str(user_match.iloc[0]['PASSWORD']).strip()
            
            # --- DEBUG VISUAL (Apague isso antes de entregar para o cliente) ---
            # Gera o hash localmente só para você ver na tela
            hash_calculado_agora = hashlib.sha256(str(password).encode('utf-8')).hexdigest()
            
            st.write("--- DEBUG INFO ---")
            st.write(f"Usuário encontrado: {username}")
            st.code(f"Hash no Banco:   {hash_banco}")
            st.code(f"Hash Digitado:   {hash_calculado_agora}")
            st.write("------------------")
            # ------------------------------------------------------------------

            # Validação Real
            if verificar_hash(password, hash_banco):
                # SUCESSO!
                nome = user_match.iloc[0].get('NOME', username)
                cargo = user_match.iloc[0].get('CARGO', 'Colaborador')
                return True, nome, cargo
            else:
                st.warning("Senha incorreta (os hashes não batem).")
                
        else:
            st.warning(f"Usuário '{username}' não encontrado na tabela.")

        return False, None, None

    except Exception as e:
        st.error(f"Erro Crítico no Auth: {e}")
        return False, None, None