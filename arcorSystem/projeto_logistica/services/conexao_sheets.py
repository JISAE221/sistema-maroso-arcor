import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import uuid
from datetime import datetime, date

# ==============================================================================
# CONFIGURAÇÕES GERAIS
# ==============================================================================

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 1. LINK DA PLANILHA (Se tiver no secrets usa, senão usa esse fixo)
LINK_PADRAO = "https://docs.google.com/spreadsheets/d/1QBMPQZ6jZJm5hEKHtRwtI1V3vZZcIkCHAqPe45N0YFE"

# 2. CREDENCIAIS HARDCODED (Fallback para desenvolvimento local)
# ⚠️ CUIDADO: Em produção, isso deve estar no st.secrets!
CREDENCIAIS_JSON = {
  "type": "service_account",
  "project_id": "sistemaarcor-482201",
  "private_key_id": "e6f42c8b535a07152fe24bcd65200003d112d658",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCdd9Cj8FwE9yjF\ncpCkiw9SG8Gsl6U3jB/FLrmiQhfMmZakbV+09DDwhFm9VJDKmvDCQhXfFyz8rnnm\nsoVQFKjs529fJcIww4S9erFyoSXcnorHOW5V4qfHwn+Huu7qwapIjJffeIdHWKdG\nlEQEHPb5oOWOKbvzuLTAdzG6jB4X4RpS4zaSUS8wCuVs6dZCT7/j4N1JMu9xEFTq\nJ9Kj9t8PyW5/z39Ffzb2m3B3GBgQt7Uc4I7ICV2UiZmh0AUeJLVEahzRiUV8STtW\nW5KsqlkzwB3zVgjOS0JVyfE9ru12YKX2wYkCJuvVKCpBHdQuIc9CGD/0ZvBxknRs\nuY4tacSBAgMBAAECggEAHFlpidY4TtmLcM6xHTp+4d6m5dJwV3mF77s7huuEutxM\n22HoiNysoeSF/njGz38JCMQaiW0z93LW9fJeX1400l/RNG1JEnvkvjMkVrmN5jPx\n0q+zfkldwPAygwZjxIZkyIZtQjmCC1V52hJP03i+ew8dPNSlJpnyirL61DWtJkmj\nYoTVbSZDRHaSPf/FdV66m9E0HzdwBcHxXedn41FOURt8oBPDDOSk4ntxRxTWesuj\nrTVJb9nu09/r2cHdSa4F23i21o+v/vVhn49HRvq6KfTomdWYVH4zVBo15udWwi8e\nF+PoGnmoN+6RzaVp8MeeS+gz4JcJPr0OzhnBW19g5QKBgQDNST6SUfkA/p1BI2H1\nF+j2Snf9Qi5y3uK7D+cEoDi+Biwmu/F4LnLhj9dpysKaOCp0+Fiu3tPBM/Z/g8fX\nYoWqcVs8sK9w4LraVXys2T99x4eZ9HJBMfeIe96QyAbftHfMQ4UTBnPHFZByj1E1\n9bzquoO8tK2ebzIzrfNBUx1WNQKBgQDEXnKHFG48ylfIY85JtekYk3wnhuIifaR4\nzjt+UkK9UElVjWNWiVQfp5nKz19Yod3k77RKhzCNMB0pdA/pqCx/GDHZoSP6v4hm\nSbc+hLoZADinx6qFy7EAMUWF8GXV86RsFe0LNVaUO3CENTFiKeNkJu4ObL34+Wct\nxeJypYEOnQKBgC2ZEFH17UZAR/O5BUAokHFsdxyE/8Y6JciBLsJDSHdE7beo1Wjp\ngFED30g7ZmBVC3Ex3JjzG7v1a9JFFjWMR75lMWvYnw+Gi1qF1IycMNMiZ8dVma9L\nhv0E7pngJE66SkXP1ZY1P7A/5PbdSJ+gtta4mRxoUYw4jMEX6UlgScrlAoGBAK1q\nz2/VrikHdRCme6aC/TDUBuANcaWOGfMKBmZflUsFHU5th94Dd4RhCiOekZB/mqu0\nuR7cVxdI92gFdIwgFfPD1Tph4ZlvDrFuxmJy6rprhJ0/aquwIEeQO9q2W+jfu0Qs\n9ONiHmzYNVy8cTlEzulCrBeXFwpKj0FQMdSXrurNAoGAYGQzkTKyOU0LcXzJyGtZ\nVhh0Th5qAbrQgD9+vZjgwIFCZhbpwT9iGN0kVFEiV+TgEfqVfHIw9t237odSFXLx\n/RsjXIxVAh42NOEC3/sw+49hBzfV0doMtp4rgayscaVPvo+6Idh9wBI2UazPLFsR\nDA3dag0B7QBrtGiDhxwNJi8=\n-----END PRIVATE KEY-----\n",
  "client_email": "logisticabot@sistemaarcor-482201.iam.gserviceaccount.com",
  "client_id": "100351585378690771993",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/logisticabot%40sistemaarcor-482201.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# ==============================================================================
# CONEXÃO OTIMIZADA (HÍBRIDA: SECRETS OU LOCAL)
# ==============================================================================
@st.cache_resource
def get_client():
    """
    Tenta conectar via st.secrets (Nuvem). Se falhar, usa a variável local (PC).
    """
    # 1. Tenta pegar do Secrets (Prioridade)
    if "CREDENCIAIS_JSON" in st.secrets:
        try:
            creds = Credentials.from_service_account_info(st.secrets["CREDENCIAIS_JSON"], scopes=SCOPE)
            return gspread.authorize(creds)
        except Exception as e:
            print(f"Aviso: Erro ao ler secrets ({e}). Tentando local...")
    
    # 2. Fallback: Usa a variável hardcoded acima
    creds = Credentials.from_service_account_info(CREDENCIAIS_JSON, scopes=SCOPE)
    return gspread.authorize(creds)

def get_worksheet(nome_aba):
    client = get_client()
    # Tenta pegar link do secrets, senão usa o padrão
    link = st.secrets.get("LINK_PLANILHA", LINK_PADRAO)
    sh = client.open_by_url(link)
    return sh.worksheet(nome_aba)

# ==============================================================================
# LEITURA DE DADOS
# ==============================================================================
@st.cache_data(ttl=30, show_spinner=False)
def carregar_dados(nome_da_aba):
    try:
        ws = get_worksheet(nome_da_aba)
        data = ws.get_all_records()
        if not data: return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Erro leitura: {e}")
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

            # Atualiza apenas se a coluna existir e tiver valor para atualizar (exceto anexos que podem ser vazios)
            for col_nome, valor in updates:
                idx = get_idx(col_nome)
                if idx:
                    # Lógica para não apagar dados existentes com string vazia se não for intencional
                    # Mas aqui assumimos que o form passa tudo.
                    if col_nome in ["COB_ANEXO", "CTE_ANEXO"] and not valor:
                        continue # Não apaga anexo se vier vazio
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
            # USER_ENTERED garante que números entrem como números
            ws.append_rows(novas_linhas, value_input_option="USER_ENTERED")
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao salvar itens: {e}")
        return False