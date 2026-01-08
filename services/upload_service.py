import cloudinary
import cloudinary.uploader
import streamlit as st
import os
import re 

# CHAVE
# =========================================================

cloudinary.config( 
  cloud_name = st.secrets["cloudinary"]["cloud_name"],
  api_key = st.secrets["cloudinary"]["api_key"], 
  api_secret = st.secrets["cloudinary"]["api_secret"],
  secure = True
)
# ==========================================================

def sanitizar_nome_arquivo(nome):
    """
    Remove caracteres inválidos do nome do arquivo para o Cloudinary.
    Cloudinary não aceita: # , + espaços e outros caracteres especiais
    """
    # Remove extensão temporariamente
    nome_base, extensao = os.path.splitext(nome)
    
    # Remove/substitui caracteres problemáticos
    nome_limpo = re.sub(r'[^\w\-_]', '_', nome_base)  # Mantém apenas letras, números, _, -
    nome_limpo = re.sub(r'_+', '_', nome_limpo)  # Remove underscores consecutivos
    nome_limpo = nome_limpo.strip('_')  # Remove _ das pontas
    nome_limpo = nome_limpo[:80]  # Limita tamanho para 80 caracteres
    
    # Recoloca extensão
    return nome_limpo + extensao

def upload_bytes_cloudinary(dados_bytes, nome_arquivo):
    """
    Faz upload de bytes (arquivo) para o Cloudinary.
    Suporta PDFs e Imagens.
    """
    try:
        tamanho = len(dados_bytes)
        print(f"\n--- 🕵️ DEBUG UPLOAD ---")
        print(f"📂 Nome Original: {nome_arquivo}")
        
        if tamanho == 0:
            print("❌ ERRO: Bytes vazios.")
            return ""

        # ✅ SANITIZA O NOME (Remove caracteres inválidos)
        nome_limpo = sanitizar_nome_arquivo(nome_arquivo)
        print(f"✅ Nome Sanitizado: {nome_limpo}")
        print(f"📊 Tamanho: {tamanho} bytes")

        # --- LÓGICA DE TIPO DE RECURSO ---
        if nome_limpo.lower().endswith(".pdf"):
            tipo_recurso = "raw"
            public_id_final = nome_limpo
        else:
            # Para imagens, remove a extensão (Cloudinary adiciona automaticamente)
            tipo_recurso = "auto"
            public_id_final = os.path.splitext(nome_limpo)[0]

        print(f"🚀 Enviando como [{tipo_recurso}]...")

        # --- UPLOAD ---
        resposta = cloudinary.uploader.upload(
            dados_bytes, 
            public_id=public_id_final, 
            resource_type=tipo_recurso,
            type="upload",
            access_mode="public",  # Garante acesso público
            overwrite=True  # Sobrescreve se já existir
        )
        
        link = resposta['secure_url']
        print(f"✅ SUCESSO: {link}\n")
        return link

    except Exception as e:
        print(f"❌ ERRO CLOUDINARY: {e}\n")
        return ""