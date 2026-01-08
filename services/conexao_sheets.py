import streamlit as st
import pandas as pd
import requests
import gspread
from google.oauth2.service_account import Credentials
import uuid
from datetime import datetime, date, timedelta, timezone
from io import StringIO

# ==============================================================================
# CONFIGURAÇÕES GERAIS
# ==============================================================================

# Mapeamento de Abas para GIDs (LEITURA)
TAB_IDS = {
    "USUARIOS": "23360391",
    "REGISTRO_ITENS": "655653628",
    "REGISTRO_MENSAGENS": "140953297",
    "REGISTRO_DEVOLUCOES": "673368922",
    "DATABASE_X3": "1758449617", 
    "DATABASE_OC": "989316476"
}

# Escopos (ESCRITA)
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ==============================================================================
# 1. LEITURA RÁPIDA (CQRS - Query) - Via Requests
# ==============================================================================
@st.cache_data(ttl=30, show_spinner=False)
def carregar_dados(nome_da_aba):
    """Lê dados via CSV export (COM DEBUG VISUAL)"""
    try:
        if "ID_PLANILHA" not in st.secrets:
            st.error("DEBUG: ID_PLANILHA não encontrado nos secrets!")
            return pd.DataFrame()
            
        sheet_id = st.secrets["ID_PLANILHA"]
        
        # DEBUG: Verifica se achou o ID da aba
        if nome_da_aba not in TAB_IDS:
            st.error(f"DEBUG: Aba '{nome_da_aba}' não encontrada no TAB_IDS. IDs disponíveis: {list(TAB_IDS.keys())}")
            return pd.DataFrame()

        gid = TAB_IDS[nome_da_aba]
        
        # Monta a URL
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        
        # DEBUG: Mostra a URL que está tentando acessar (apague depois)
        # st.write(f"Tentando baixar: {url}") 
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # Se der erro 400 ou 500, vai cair no except
        response.raise_for_status() 
        response.encoding = 'utf-8'
        
        df = pd.read_csv(StringIO(response.text)).fillna("")
        
        # DEBUG: Verifica se o CSV veio vazio
        if df.empty:
            st.warning(f"DEBUG: A conexão funcionou, mas a aba '{nome_da_aba}' (GID {gid}) está vazia!")
            
        return df
        
    except Exception as e:
        st.error(f"DEBUG ERRO FATAL ({nome_da_aba}): {e}")
        return pd.DataFrame()

def carregar_itens_por_processo(id_processo):
    df = carregar_dados("REGISTRO_ITENS")
    if not df.empty and "ID_PROCESSO" in df.columns:
        df["ID_PROCESSO"] = df["ID_PROCESSO"].astype(str)
        return df[df["ID_PROCESSO"] == str(id_processo)]
    return pd.DataFrame()

def carregar_mensagens(id_processo):
    df = carregar_dados("REGISTRO_MENSAGENS")
    if not df.empty and "ID_PROCESSO" in df.columns:
        df["ID_PROCESSO"] = df["ID_PROCESSO"].astype(str)
        return df[df["ID_PROCESSO"] == str(id_processo)].sort_values("DATA_HORA")
    return pd.DataFrame()

# ==============================================================================
# 2. ESCRITA SEGURA (CQRS - Command) - Via API Gspread
# ==============================================================================

# --- OTIMIZAÇÃO SÊNIOR: Cache na Autenticação ---
@st.cache_resource
def get_gspread_client():
    # 1. Valida se a seção existe
    if "gcp" not in st.secrets:
        st.error("Configuração Faltando: Seção '[gcp]' não encontrada.")
        return None

    try:
        # 2. PEGA A CHAVE PRIVADA
        pk = st.secrets["gcp"]["private_key"]

        # 3. Monta o Dicionário Limpo
        creds_dict = {
            "type": st.secrets["gcp"]["type"],
            "project_id": st.secrets["gcp"]["project_id"],
            "private_key_id": st.secrets["gcp"]["private_key_id"],
            "private_key": pk,
            "client_email": st.secrets["gcp"]["client_email"],
            "client_id": st.secrets["gcp"]["client_id"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": st.secrets["gcp"]["client_x509_cert_url"]
        }
        
        # 4. Tenta AutenticarQ
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        return gspread.authorize(creds)

    except Exception as e:
        debug_key = st.secrets["gcp"]["private_key"][:50] if "gcp" in st.secrets else "N/A"
        st.error(f"Erro Fatal Auth: {e} | Início da chave lida: {debug_key}...")
        return None
    
def get_worksheet_write(nome_aba):
    """Pega a aba usando o cliente cacheado."""
    client = get_gspread_client()
    if not client: return None
    
    try:
        # Abre planilha pelo ID
        sh = client.open_by_key(st.secrets["ID_PLANILHA"])
        return sh.worksheet(nome_aba)
    except Exception as e:
        st.error(f"Erro ao abrir aba '{nome_aba}': {e}")
        return None

# ==============================================================================
# FUNÇÕES DE COMANDO (SALVAR/ATUALIZAR)
# ==============================================================================

def salvar_mensagem(id_processo, usuario, texto, link_anexo=""):
    try:
        ws = get_worksheet_write("REGISTRO_MENSAGENS")
        if not ws: return False
        
        nova_msg = [
            str(uuid.uuid4())[:8],
            str(id_processo),
            (datetime.now(timezone.utc)+timedelta(hours=-3)).strftime("%Y-%m-%d %H:%M:%S"),
            str(usuario),
            str(texto),
            str(link_anexo)
        ]
        ws.append_row(nova_msg)
        st.cache_data.clear() # Limpa cache para refletir na hora
        return True
    except Exception as e:
        st.error(f"Erro ao salvar mensagem: {e}")
        return False

def gerar_id_processo():
    try:
        # Usa LEITURA RÁPIDA (csv) para calcular o próximo ID
        df = carregar_dados("REGISTRO_DEVOLUCOES")
        
        if df.empty or "ID_PROCESSO" not in df.columns:
             return f"#DEV{(datetime.now(timezone.utc)+timedelta(hours=-3)).strftime('%Y%m%d-%H%M%S')}"
             
        # Converte para string para garantir
        ids_existentes = df["ID_PROCESSO"].astype(str).tolist()
        ids_dev = [x for x in ids_existentes if str(x).startswith("#DEV")]
        
        if not ids_dev:
            seq = 1
        else:
            numeros = []
            for id_proc in ids_dev:
                try:
                    parts = id_proc.split('-')
                    if len(parts) > 1:
                        num = int(parts[-1])
                        numeros.append(num)
                except: continue
            seq = max(numeros) + 1 if numeros else 1
        
        ano_mes = (datetime.now(timezone.utc)+timedelta(hours=-3)).strftime("%Y%m")
        return f"#DEV{ano_mes}-{seq:03d}"
        
    except Exception as e:
        print(f"Erro ao gerar ID: {e}")
        return f"#DEV{(datetime.now(timezone.utc)+timedelta(hours=-3)).strftime('%Y%m%d-%H%M%S')}"

def salvar_novo_processo(dados):
    try:
        ws = get_worksheet_write("REGISTRO_DEVOLUCOES")
        if not ws: return False, None

        id_processo = gerar_id_processo()
        data_hoje = (datetime.now(timezone.utc)+timedelta(hours=-3)).strftime("%d/%m/%Y %H:%M:%S")
        
        headers = ws.row_values(1)
        nova_linha = [""] * len(headers)
        
        mapa_colunas = {
            "ID_PROCESSO": "ID_PROCESSO",
            "DATA_CRIACAO": "DATA_CRIACAO",
            "STATUS": "STATUS",
            "COB_DATA": "COB_DATA",
            "ORDEM_DE_CARGA": "ORDEM_DE_CARGA",
            "DATA_DEVOLUCAO_CTE": "DATA_DEVOLUCAO_CTE",
            "NF": "NF",
            "CTE": "CTE",
            "DATA_EMISSAO": "DATA_EMISSAO",
            "VEICULO": "VEICULO",
            "TIPO_VEICULO": "TIPO_VEICULO",
            "MOTORISTA": "MOTORISTA",
            "OC": "OC",
            "DATA_INICIO": "DATA_INICIO",
            "DATA_FIM": "DATA_FIM",
            "STATUS_OC": "STATUS_OC",
            "PRAZO": "PRAZO",
            "TIPO_CARGA": "TIPO_CARGA",
            "LOCAL": "LOCAL",
            "MOTIVO": "MOTIVO",
            "RESPONSAVEL": "RESPONSAVEL",
            "LINK_NFD": "LINK_NFD" 
        }
        
        for chave_pacote, nome_coluna in mapa_colunas.items():
            if nome_coluna in headers:
                index = headers.index(nome_coluna)
                if chave_pacote == "ID_PROCESSO": nova_linha[index] = id_processo
                elif chave_pacote == "DATA_CRIACAO": nova_linha[index] = data_hoje
                elif chave_pacote == "STATUS": nova_linha[index] = "ABERTO"
                else: nova_linha[index] = str(dados.get(chave_pacote, ""))

        ws.append_row(nova_linha)
        st.cache_data.clear()
        return True, id_processo

    except Exception as e:
        st.error(f"Erro ao salvar processo: {e}")
        return False, None

def salvar_dataframe(nome_da_aba, df):
    try:
        ws = get_worksheet_write(nome_da_aba)
        if not ws: return False
        
        ws.clear()
        # Converte tudo para string para evitar erros de serialização JSON
        df = df.fillna("").astype(str) 
        lista_dados = [df.columns.values.tolist()] + df.values.tolist()
        ws.update(lista_dados)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro delete: {e}")
        return False

def excluir_processo_completo(id_processo):
    abas_alvo = ["REGISTRO_DEVOLUCOES", "REGISTRO_ITENS", "REGISTRO_MENSAGENS"]
    erros = []
    
    for aba in abas_alvo:
        try:
            # Lê via CSV (Rápido)
            df = carregar_dados(aba)
            if not df.empty and "ID_PROCESSO" in df.columns:
                df["ID_PROCESSO"] = df["ID_PROCESSO"].astype(str) # Garante tipagem
                mascara = df["ID_PROCESSO"] == str(id_processo)
                
                if mascara.any():
                    # Filtra e reescreve a aba inteira (Estratégia mais segura que deletar linha a linha)
                    df_novo = df[~mascara]
                    salvar_dataframe(aba, df_novo)
        except Exception as e:
            erros.append(f"Erro na aba {aba}: {str(e)}")
    
    return len(erros) == 0

def atualizar_tratativa_completa(id_processo, novo_status_log, novo_status_fisc, cod_cob, link_anexo_cob, link_anexo_cte, cod_cte, veiculo, motorista, local_atual, local_destino, oc, data_cte, cob_data, ordem_de_carga):
    try:
        ws = get_worksheet_write("REGISTRO_DEVOLUCOES")
        if not ws: return False
        
        cell = ws.find(id_processo)
        
        if cell:
            header = ws.row_values(1)
            def get_idx(nome):
                try: return header.index(nome) + 1
                except ValueError: return None
            
            # Formatação segura de datas
            dt_cte = data_cte.strftime("%d/%m/%Y") if isinstance(data_cte, (date, datetime)) else str(data_cte)
            dt_cob = cob_data.strftime("%d/%m/%Y") if isinstance(cob_data, (date, datetime)) else str(cob_data)

            updates = [
                ("STATUS", novo_status_log),
                ("STATUS_FISCAL", novo_status_fisc),
                ("COD_COB", cod_cob),
                ("COB_ANEXO", link_anexo_cob),
                ("COD_CTE", cod_cte),
                ("DATA_DEVOLUCAO_CTE", dt_cte),
                ("COB_DATA", dt_cob),
                ("CTE_ANEXO", link_anexo_cte),
                ("VEICULO", veiculo),
                ("ORDEM_DE_CARGA", ordem_de_carga),
                ("OC", oc),
                ("MOTORISTA", motorista),
                ("LOCAL_ATUAL", local_atual),
                ("LOCAL_DESTINO", local_destino)
            ]

            # Nota de Performance: Isso aqui faz 1 request por célula. 
            # Em produção massiva, deveríamos usar batch_update, mas para uso atual está ok.
            for col_nome, valor in updates:
                idx = get_idx(col_nome)
                if idx:
                    # Lógica para não apagar anexo se vier vazio
                    if col_nome in ["COB_ANEXO", "CTE_ANEXO"] and not valor:
                        continue 
                    ws.update_cell(cell.row, idx, valor)
            
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao atualizar tratativa: {e}")
        return False

def atualizar_status_devolucao(id_processo, novo_status):
    try:
        ws = get_worksheet_write("REGISTRO_DEVOLUCOES")
        if not ws: return False
        
        cell = ws.find(id_processo)
        if cell:
            header = ws.row_values(1)
            col_index = header.index("STATUS") + 1 if "STATUS" in header else 8
            ws.update_cell(cell.row, col_index, novo_status)
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao atualizar status: {e}")
        return False
    
def salvar_itens_lote(id_processo, lista_itens):
    try:
        ws = get_worksheet_write("REGISTRO_ITENS")
        if not ws: return False

        headers = ws.row_values(1)
        data_agora = (datetime.now(timezone.utc)+timedelta(hours=-3)).strftime("%d/%m/%Y %H:%M:%S")
        novas_linhas = []
        
        for item in lista_itens:
            nova_linha = [""] * len(headers)
            mapa = {
                "ID_ITEM": str(uuid.uuid4())[:8],
                "ID_PROCESSO": str(id_processo),
                "DATA_REGISTRO": data_agora,
                "NUMERO_NFD": str(item.get("NUMERO_NFD", "")),
                "COD_ITEM": str(item.get("COD_ITEM", "")),
                "DESCRICAO": str(item.get("DESCRICAO", "")),
                "QTD": str(item.get("QTD", "")),
                "VALOR_UNIT": str(item.get("VALOR_UNIT", "")),
                "VALOR_TOTAL": str(item.get("VALOR_TOTAL", ""))
            }
            for chave, valor in mapa.items():
                if chave in headers:
                    nova_linha[headers.index(chave)] = valor
            novas_linhas.append(nova_linha)
        
        if novas_linhas:
            # append_rows é eficiente (1 request para N linhas)
            ws.append_rows(novas_linhas, value_input_option="USER_ENTERED")
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao salvar itens: {e}")
        return False