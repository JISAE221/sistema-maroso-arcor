import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import uuid
from datetime import datetime, date

# ==============================================================================
# CONFIGURAÇÕES DE SEGURANÇA
# ==============================================================================

# Escopos necessários para acessar o Google Drive e Sheets
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ==============================================================================
# CONEXÃO OTIMIZADA (VIA SECRETS)
# ==============================================================================
@st.cache_resource
def get_client():
    """
    Conecta ao Google Sheets usando EXCLUSIVAMENTE os Segredos do Streamlit.
    Não há fallback para variáveis hardcoded por segurança.
    """
    # Verifica se as credenciais existem no secrets.toml (Local) ou Secrets (Cloud)
    if "CREDENCIAIS_JSON" not in st.secrets:
        st.error("🚨 ERRO CRÍTICO: Credenciais não encontradas nos Secrets.")
        st.stop()
        return None

    try:
        # Carrega as credenciais direto do dicionário seguro
        creds_dict = dict(st.secrets["CREDENCIAIS_JSON"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"🚨 Erro de Autenticação: {e}")
        st.stop()
        return None

def get_worksheet(nome_aba):
    """
    Abre uma aba específica usando o ID da planilha armazenado nos Secrets.
    """
    client = get_client()
    if not client: return None

    # Busca o ID da Planilha nos Secrets
    spreadsheet_id = st.secrets.get("ID_PLANILHA")
    
    if not spreadsheet_id:
        st.error("🚨 Configuração Faltando: 'ID_PLANILHA' não encontrado nos Secrets.")
        st.stop()
        return None

    try:
        # Abre pelo ID (Mais seguro e rápido que URL)
        sh = client.open_by_key(spreadsheet_id)
        return sh.worksheet(nome_aba)
    except Exception as e:
        # Erro comum: A aba não existe ou o ID está errado
        print(f"Erro ao abrir aba '{nome_aba}': {e}")
        return None

# ==============================================================================
# LEITURA DE DADOS
# ==============================================================================
@st.cache_data(ttl=30, show_spinner=False)
def carregar_dados(nome_da_aba):
    try:
        ws = get_worksheet(nome_da_aba)
        if not ws: return pd.DataFrame()
        
        data = ws.get_all_records()
        if not data: return pd.DataFrame()
        
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Erro leitura ({nome_da_aba}): {e}")
        return pd.DataFrame()

def carregar_itens_por_processo(id_processo):
    try:
        df = carregar_dados("REGISTRO_ITENS")
        if not df.empty and "ID_PROCESSO" in df.columns:
            return df[df["ID_PROCESSO"] == id_processo]
    except: pass
    return pd.DataFrame()

def carregar_mensagens(id_processo):
    df = carregar_dados("REGISTRO_MENSAGENS")
    if not df.empty and "ID_PROCESSO" in df.columns:
        return df[df["ID_PROCESSO"] == id_processo].sort_values("DATA_HORA")
    return pd.DataFrame()

# ==============================================================================
# ESCRITA E ATUALIZAÇÃO
# ==============================================================================

def salvar_mensagem(id_processo, usuario, texto, link_anexo=""):
    try:
        ws = get_worksheet("REGISTRO_MENSAGENS")
        if not ws: return False
        
        nova_msg = [
            str(uuid.uuid4())[:8],
            id_processo,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            usuario,
            texto,
            link_anexo
        ]
        ws.append_row(nova_msg)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar mensagem: {e}")
        return False
    
def gerar_id_processo():
    try:
        ws = get_worksheet("REGISTRO_DEVOLUCOES")
        if not ws: return f"#DEV{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        col_ids = ws.col_values(1)
        ids_existentes = [id_val for id_val in col_ids[1:] if id_val and id_val.startswith("#DEV")]
        
        if not ids_existentes:
            seq = 1
        else:
            numeros = []
            for id_proc in ids_existentes:
                try:
                    num = int(id_proc.split('-')[-1])
                    numeros.append(num)
                except: continue
            seq = max(numeros) + 1 if numeros else 1
        
        ano_mes = datetime.now().strftime("%Y%m")
        return f"#DEV{ano_mes}-{seq:03d}"
        
    except Exception as e:
        print(f"Erro ao gerar ID: {e}")
        return f"#DEV{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
def salvar_novo_processo(dados):
    try:
        ws = get_worksheet("REGISTRO_DEVOLUCOES")
        if not ws: return False, None

        id_processo = gerar_id_processo()
        data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
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

# --- AUXILIAR DELETAR ---
def salvar_dataframe(nome_da_aba, df):
    try:
        ws = get_worksheet(nome_da_aba)
        if not ws: return False
        
        ws.clear()
        df = df.astype(str)
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
            df = carregar_dados(aba)
            if not df.empty and "ID_PROCESSO" in df.columns:
                mascara = df["ID_PROCESSO"] == id_processo
                if mascara.any():
                    df_novo = df[~mascara]
                    salvar_dataframe(aba, df_novo)
        except Exception as e:
            erros.append(f"Erro na aba {aba}: {str(e)}")
    
    return len(erros) == 0

def atualizar_tratativa_completa(id_processo, novo_status_log, novo_status_fisc, cod_cob, link_anexo_cob, link_anexo_cte, cod_cte, veiculo, motorista, local_atual, local_destino, oc, data_cte, cob_data, ordem_de_carga):
    try:
        ws = get_worksheet("REGISTRO_DEVOLUCOES")
        if not ws: return False
        
        cell = ws.find(id_processo)
        
        if cell:
            header = ws.row_values(1)
            def get_idx(nome):
                try: return header.index(nome) + 1
                except ValueError: return None
            
            # Mapeamento
            updates = [
                ("STATUS", novo_status_log),
                ("STATUS_FISCAL", novo_status_fisc),
                ("COD_COB", cod_cob),
                ("COB_ANEXO", link_anexo_cob),
                ("COD_CTE", cod_cte),
                ("DATA_DEVOLUCAO_CTE", data_cte.strftime("%d/%m/%Y") if isinstance(data_cte, (date, datetime)) else str(data_cte)),
                ("COB_DATA", cob_data.strftime("%d/%m/%Y") if isinstance(cob_data, (date, datetime)) else str(cob_data)),
                ("CTE_ANEXO", link_anexo_cte),
                ("VEICULO", veiculo),
                ("ORDEM_DE_CARGA", ordem_de_carga),
                ("OC", oc),
                ("MOTORISTA", motorista),
                ("LOCAL_ATUAL", local_atual),
                ("LOCAL_DESTINO", local_destino)
            ]

            for col_nome, valor in updates:
                idx = get_idx(col_nome)
                if idx:
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
        ws = get_worksheet("REGISTRO_DEVOLUCOES")
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
        ws = get_worksheet("REGISTRO_ITENS")
        if not ws: return False

        headers = ws.row_values(1)
        data_agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        novas_linhas = []
        
        for item in lista_itens:
            nova_linha = [""] * len(headers)
            mapa = {
                "ID_ITEM": str(uuid.uuid4())[:8],
                "ID_PROCESSO": id_processo,
                "DATA_REGISTRO": data_agora,
                "NUMERO_NFD": item.get("NUMERO_NFD", ""),
                "COD_ITEM": item.get("COD_ITEM", ""),
                "DESCRICAO": item.get("DESCRICAO", ""),
                "QTD": item.get("QTD", ""),
                "VALOR_UNIT": item.get("VALOR_UNIT", ""),
                "VALOR_TOTAL": item.get("VALOR_TOTAL", "")
            }
            for chave, valor in mapa.items():
                if chave in headers:
                    nova_linha[headers.index(chave)] = valor
            novas_linhas.append(nova_linha)
        
        if novas_linhas:
            ws.append_rows(novas_linhas, value_input_option="USER_ENTERED")
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao salvar itens: {e}")
        return False