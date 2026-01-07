import streamlit as st
import pandas as pd
import base64
import uuid
import re 
from datetime import datetime
from services.conexao_sheets import carregar_dados, salvar_novo_processo, salvar_itens_lote
from services.upload_service import upload_bytes_cloudinary
from pathlib import Path

# Proteção de acesso
if "logado" not in st.session_state or not st.session_state["logado"]:
    st.switch_page("app.py")

# ==============================================================================
# CSS: TRAVAR BARRA LATERAL (FULL HEIGHT)
# ==============================================================================
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"] > div {
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding-top: 0px !important;
        padding-bottom: 20px !important;
    }
    div[data-testid="stSidebarUserContent"] {
        padding-top: 2rem !important;
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    div[data-testid="stImage"] { margin-bottom: 20px; }
    .footer-container { margin-top: auto; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    try:
        logo_path = "assets/logo.png"
        st.image(logo_path, use_container_width=True)
    except:
        st.header("MAROSO")

    st.write("") 
    st.caption("MENU PRINCIPAL")
    
    st.page_link("pages/1_📊_Dashboard.py", label="Dashboard", icon="📊") 
    st.page_link("pages/2_🚛_Processo_Devolucao.py", label="Novo Processo", icon="🚛")
    st.page_link("pages/3_📋_Gestao_Tratativas.py", label="Gestão Tratativas", icon="📋")
    st.page_link("pages/4_📍_Posições.py", label="Posições & Rotas", icon="📍") 

    st.markdown('<div class="footer-container">', unsafe_allow_html=True)
    st.markdown("---")
    c_perfil, c_texto = st.columns([0.25, 0.75])
    with c_perfil:
        st.markdown("""<div style='font-size: 24px; text-align: center; background: #262730; border-radius: 50%; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; border: 1px solid #444;'>👤</div>""", unsafe_allow_html=True)
        
    with c_texto:
        usuario_nome = st.session_state.get('usuario', 'Admin').split(' ')[0].title()
        st.markdown(f"""<div style='line-height: 1.2;'><span style='font-weight: bold; font-size: 14px;'>{usuario_nome}</span><br><span style='font-size: 11px; color: #888;'>Maroso Transporte</span></div>""", unsafe_allow_html=True)

    st.write("")
    if st.button("Sair do Sistema", use_container_width=True):
        st.session_state["logado"] = False
        st.switch_page("app.py")
        
    st.markdown('</div>', unsafe_allow_html=True)

# ... Constantes ...
COL_X3_NF = "Nota Fiscal"
COL_X3_CTE = "Nº CTe"
COL_X3_DATA = "Dt. Emissão CTe"
COL_X3_VEICULO = "CARRETABARRA"      
COL_X3_TIPO = "Tipo Equip."
COL_X3_LOCAL = "Cidade Início"
COL_X3_MOTORISTA = "Motorista"
COL_OC_MOTIVO = "Notas fiscais - motivo"
COL_OC_DATA_INI = "Data do problema"
COL_OC_DATA_FIM = "Data do encerramento"
COL_OC_OCORRENCIA = "Ocorrência"

def calcular_prazo_alerta(data_emissao_str):
    try:
        if not data_emissao_str or str(data_emissao_str).strip() == "": return "SEM DATA", "grey"
        dt_emissao = pd.to_datetime(data_emissao_str, dayfirst=True).date()
        hoje = datetime.now().date()
        dias_corridos = (hoje - dt_emissao).days
        if dias_corridos < 3: return f"FRESCO (<3 dias)", "#00B17C"
        elif dias_corridos < 5: return f"ATENÇÃO (<5 dias)", "#5173C2"
        elif dias_corridos < 10: return f"DENTRO DO PRAZO DE 10", "#EC9E55"
        elif dias_corridos < 20: return f"DENTRO DO PRAZO DE 20", "#E9EB7B"
        else: return f"ESTOUROU 20 DIAS ({dias_corridos} dias)", "#DB6464"
    except: return "DATA INVÁLIDA", "grey"

# --- MEMÓRIA TEMPORÁRIA ---
if 'lista_itens_temp' not in st.session_state: st.session_state['lista_itens_temp'] = []
if 'aba_ativa' not in st.session_state: st.session_state['aba_ativa'] = "1. Ocorrência"
if 'cache_nfd_arquivo' not in st.session_state: st.session_state['cache_nfd_arquivo'] = None

# --- TÍTULO ---
st.markdown(f"# Processo de Devolução", unsafe_allow_html=True)

# --- BARRA DE BUSCA ---
col_busca, col_btn = st.columns([4, 1])
with col_busca:
    nf_busca = st.text_input("Digite a NF", placeholder="Ex: 38435")
with col_btn:
    st.write("")
    st.write("")
    btn_buscar = st.button("🔍 Buscar", type="primary")

if btn_buscar and nf_busca:
    # 1. Limpa Estado e Caches
    st.session_state['dados_encontrados'] = {} 
    st.session_state['status_busca'] = "novo" 
    st.session_state['lista_itens_temp'] = []
    st.session_state['cache_nfd_arquivo'] = None
    
    # Lista de chaves para limpar (Inputs + Caches)
    keys_clean = [
        'input_veiculo', 'cache_veiculo',
        'input_tip_veiculo', 'cache_tip_veiculo',
        'input_motorista', 'cache_motorista',
        'input_oc', 'cache_oc',
        'input_dt_ini', 'cache_dt_ini',
        'input_dt_fim', 'cache_dt_fim',
        'input_tipo_carga', 'cache_tipo_carga',
        'input_ordem_de_carga', 'cache_ordem',
        'input_data_devolucao', 'cache_data_devolucao',
        'input_local_atual', 'cache_local_atual',     # <--- NOVO
        'input_local_destino', 'cache_local_destino', # <--- NOVO
        'upload_geral'
    ]
    for k in keys_clean: 
        if k in st.session_state: del st.session_state[k]
    
    st.session_state['aba_ativa'] = "1. Ocorrência" 
    
    # 2. Busca
    df_reg = carregar_dados("REGISTRO_DEVOLUCOES")
    ja_existe = False
    dados_existentes = {} 
    
    if not df_reg.empty and "NF" in df_reg.columns:
        df_reg["NF_STR"] = df_reg["NF"].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        busca_limpa = str(nf_busca).strip()
        filtro_reg = df_reg[df_reg["NF_STR"] == busca_limpa]
        if not filtro_reg.empty:
            ja_existe = True
            dados_existentes = filtro_reg.iloc[0].to_dict()
            st.warning(f"⚠️ Processo já registrado! ID: {dados_existentes.get('ID_PROCESSO')}")
            st.session_state['status_busca'] = "existente"
            
            st.session_state['dados_encontrados'] = {
                "NF": dados_existentes.get("NF", ""),
                "CTE": dados_existentes.get("CTE", ""),
                "DATA_EMISSAO": dados_existentes.get("DATA_EMISSAO", ""),
                "OC": dados_existentes.get("OC", ""),
                "LOCAL": dados_existentes.get("LOCAL", ""),
                "LOCAL_DESTINO": dados_existentes.get("LOCAL_DESTINO", ""), # <--- Recupera Destino
                "ORDEM_DE_CARGA": dados_existentes.get("ORDEM_DE_CARGA","") or dados_existentes.get("ORDEM_DE_CARGA",""),
                "MOTIVO_COMPLETO": dados_existentes.get("MOTIVO", ""),
                "RESPONSAVEL": dados_existentes.get("RESPONSAVEL", ""),
                "VEICULO": dados_existentes.get("VEICULO", ""),
                "TIPO_VEICULO": dados_existentes.get("TIPO_VEICULO", ""),
                "MOTORISTA": dados_existentes.get("MOTORISTA", ""),
                "DATA_INICIO": dados_existentes.get("DATA_INICIO", ""),
                "DATA_FIM": dados_existentes.get("DATA_FIM", ""),
                "TIPO_CARGA": dados_existentes.get("TIPO_CARGA", "DIRETA"),
                "DATA_DEVOLUCAO_CTE": dados_existentes.get("DATA_DEVOLUCAO_CTE", "")
            }

    # 3. Inicializa CACHES (Blindagem de Dados)
    def get_val(chave, alt=""): return str(dados_existentes.get(chave, "") or alt) if ja_existe else ""
    
    st.session_state['cache_veiculo'] = get_val("VEICULO")
    st.session_state['cache_tip_veiculo'] = get_val("TIPO_VEICULO")
    st.session_state['cache_motorista'] = get_val("MOTORISTA")
    st.session_state['cache_oc'] = get_val("OC")
    st.session_state['cache_ordem'] = str(dados_existentes.get("ORDEM_DE_CARGA", "") or dados_existentes.get("ORDEM_DE_CARGA", "") or "") if ja_existe else ""
    st.session_state['cache_dt_ini'] = get_val("DATA_INICIO", datetime.now().strftime("%d/%m/%Y"))
    st.session_state['cache_dt_fim'] = get_val("DATA_FIM")
    st.session_state['cache_tipo_carga'] = get_val("TIPO_CARGA", "DIRETA")
    
    # Novos Caches de Local
    st.session_state['cache_local_atual'] = get_val("LOCAL")
    st.session_state['cache_local_destino'] = get_val("LOCAL_DESTINO")

    try:
        if ja_existe and dados_existentes.get("DATA_DEVOLUCAO_CTE"):
             st.session_state['cache_data_devolucao'] = pd.to_datetime(dados_existentes.get("DATA_DEVOLUCAO_CTE"), dayfirst=True).date()
        else:
             st.session_state['cache_data_devolucao'] = datetime.now().date()
    except:
        st.session_state['cache_data_devolucao'] = datetime.now().date()


    # 4. Busca Bases Externas (Se Novo)
    if not ja_existe:
        with st.spinner("Consultando bases de dados..."):
            df_x3 = carregar_dados("DATABASE_X3")
            df_oc = carregar_dados("DATABASE_OC")
            if not df_x3.empty: df_x3.columns = df_x3.columns.str.strip()
            if not df_oc.empty: df_oc.columns = df_oc.columns.str.strip()

            res_x3, res_oc = {}, {}
            busca_limpa = str(nf_busca).strip()

            if COL_X3_NF in df_x3.columns:
                df_x3["_NF_BUSCA"] = df_x3[COL_X3_NF].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                f_x3 = df_x3[df_x3["_NF_BUSCA"] == busca_limpa]
                if not f_x3.empty: res_x3 = f_x3.iloc[0].to_dict()
                else:
                    f_x3_part = df_x3[df_x3["_NF_BUSCA"].str.contains(busca_limpa, na=False)]
                    if not f_x3_part.empty: res_x3 = f_x3_part.iloc[0].to_dict()

            if COL_OC_MOTIVO in df_oc.columns:
                f_oc = df_oc[df_oc[COL_OC_MOTIVO].astype(str).str.contains(busca_limpa, na=False)]
                if not f_oc.empty: res_oc = f_oc.iloc[0].to_dict()

            if res_x3 or res_oc:
                st.success("✅ Dados encontrados!")
                motivo_bruto = res_oc.get(COL_OC_MOTIVO, "")
                motivo_limpo = motivo_bruto 
                if motivo_bruto:
                    linhas = str(motivo_bruto).split('\n')
                    for linha in linhas:
                        if nf_busca in linha:
                            partes = linha.split('-', 1) 
                            motivo_limpo = partes[1].strip() if len(partes) > 1 else linha
                            break 
                
                # Preenche Cache com dados encontrados
                st.session_state['cache_veiculo'] = str(res_x3.get(COL_X3_VEICULO, "") or "")
                st.session_state['cache_tip_veiculo'] = str(res_x3.get(COL_X3_TIPO,"") or "")
                st.session_state['cache_motorista'] = str(res_x3.get(COL_X3_MOTORISTA, "") or "")
                st.session_state['cache_oc'] = str(res_oc.get(COL_OC_OCORRENCIA, "") or "")
                st.session_state['cache_dt_ini'] = str(res_oc.get(COL_OC_DATA_INI, "") or datetime.now().strftime("%d/%m/%Y"))
                st.session_state['cache_dt_fim'] = str(res_oc.get(COL_OC_DATA_FIM, "") or "")
                st.session_state['cache_local_atual'] = str(res_x3.get(COL_X3_LOCAL, "") or "") # <--- Pega Local do X3
                st.session_state['cache_local_destino'] = "" # Novo começa vazio
                
                st.session_state['dados_encontrados'] = {
                    "NF": nf_busca, 
                    "CTE": res_x3.get(COL_X3_CTE, ""),
                    "DATA_EMISSAO": res_x3.get(COL_X3_DATA, ""),
                    "LOCAL": res_x3.get(COL_X3_LOCAL, ""),
                    "MOTIVO_COMPLETO": motivo_limpo,
                    "TIPO_CARGA": "DIRETA"
                }
            else:
                st.error("❌ NF não encontrada.")

st.divider()

# --- ÁREA DO FORMULÁRIO ---
dados = st.session_state.get('dados_encontrados', {})
modo = st.session_state.get('status_busca', 'novo')

if dados:
    if modo == "existente": st.info("👁️ Modo Visualização")
    else: st.caption("✨ Novo Cadastro")

    dt_emissao = dados.get("DATA_EMISSAO")
    
    # === SINCRONIA: SALVA INPUTS NO CACHE ANTES DE MUDAR ABA ===
    # Se os widgets existem na tela, atualiza o cofre
    if "input_veiculo" in st.session_state: st.session_state['cache_veiculo'] = st.session_state["input_veiculo"]
    if "input_ordem_de_carga" in st.session_state: st.session_state['cache_ordem'] = st.session_state["input_ordem_de_carga"]
    if "input_tip_veiculo" in st.session_state: st.session_state['cache_tip_veiculo'] = st.session_state["input_tip_veiculo"]
    if "input_motorista" in st.session_state: st.session_state['cache_motorista'] = st.session_state["input_motorista"]
    if "input_oc" in st.session_state: st.session_state['cache_oc'] = st.session_state["input_oc"]
    if "input_dt_ini" in st.session_state: st.session_state['cache_dt_ini'] = st.session_state["input_dt_ini"]
    if "input_dt_fim" in st.session_state: st.session_state['cache_dt_fim'] = st.session_state["input_dt_fim"]
    if "input_tipo_carga" in st.session_state: st.session_state['cache_tipo_carga'] = st.session_state["input_tipo_carga"]
    if "input_data_devolucao" in st.session_state: st.session_state['cache_data_devolucao'] = st.session_state["input_data_devolucao"]
    
    # Novos Campos de Local
    if "input_local_atual" in st.session_state: st.session_state['cache_local_atual'] = st.session_state["input_local_atual"]
    if "input_local_destino" in st.session_state: st.session_state['cache_local_destino'] = st.session_state["input_local_destino"]

    opcoes_abas = ["1. Ocorrência", "2. Itens (NFD)"]
    aba_selecionada = st.radio("Etapas:", opcoes_abas, horizontal=True, key="aba_ativa", label_visibility="collapsed")
    st.divider()

    # --- ABA 1: OCORRÊNCIA ---
    if aba_selecionada == "1. Ocorrência":
        
        def pre_salvar_ordem():
            st.session_state['cache_ordem'] = st.session_state.get("input_ordem_de_carga", "")
            st.toast(f"✅ Ordem {st.session_state['cache_ordem']} memorizada!", icon="💾")
            
        # RESTAURAÇÃO: Inicializa inputs com valor do CACHE
        if "input_veiculo" not in st.session_state: st.session_state["input_veiculo"] = st.session_state.get("cache_veiculo", "")
        if "input_ordem_de_carga" not in st.session_state: st.session_state["input_ordem_de_carga"] = st.session_state.get("cache_ordem", "")
        if "input_tip_veiculo" not in st.session_state: st.session_state["input_tip_veiculo"] = st.session_state.get("cache_tip_veiculo", "")
        if "input_motorista" not in st.session_state: st.session_state["input_motorista"] = st.session_state.get("cache_motorista", "")
        if "input_oc" not in st.session_state: st.session_state["input_oc"] = st.session_state.get("cache_oc", "")
        if "input_dt_ini" not in st.session_state: st.session_state["input_dt_ini"] = st.session_state.get("cache_dt_ini", "")
        if "input_dt_fim" not in st.session_state: st.session_state["input_dt_fim"] = st.session_state.get("cache_dt_fim", "")
        if "input_tipo_carga" not in st.session_state: st.session_state["input_tipo_carga"] = "DIRETA"
        if "input_local_atual" not in st.session_state: st.session_state["input_local_atual"] = st.session_state.get("cache_local_atual", "")
        if "input_local_destino" not in st.session_state: st.session_state["input_local_destino"] = st.session_state.get("cache_local_destino", "")
        
        if "input_data_devolucao" not in st.session_state: 
            st.session_state["input_data_devolucao"] = st.session_state.get("cache_data_devolucao", datetime.now().date())

        # Layout Inputs (Todos usando Key)
        c42, c1, c2, c3, = st.columns(4)
        c42.text_input("Ordem de Carga", key="input_ordem_de_carga", disabled=(modo=="existente"), on_change=pre_salvar_ordem)
        c1.text_input("CTE", value=dados.get("CTE", ""), disabled=True)
        c2.date_input("Data Devolução", key="input_data_devolucao", format="DD/MM/YYYY", disabled=(modo=="existente"))
        c3.text_input("NF Buscada", value=dados.get("NF", ""), disabled=True)

        c4, c5, c6, c7 = st.columns(4)
        c4.text_input("Veículo", key="input_veiculo", disabled=(modo=="existente"))
        c5.text_input("Tipo Veículo", key="input_tip_veiculo", disabled=(modo=="existente"))
        
        # Correção aqui: Campo Local agora é editável e usa cache
        c6.text_input("Local Atual", key="input_local_atual", disabled=(modo=='existente'))
        c7.text_input("Motorista", key="input_motorista", disabled=(modo=="existente"))

        st.write("")
        st.markdown("##### 📅 Dados da Ocorrência")
        c_tipo, c_oc, c_ini, c_fim = st.columns(4)
        
        idx_tipo = 0
        if st.session_state.get("cache_tipo_carga") == "ARMAZENAGEM": idx_tipo = 1
        
        c_tipo.selectbox("Tipo de Carga", ["DIRETA", "ARMAZENAGEM"], index=idx_tipo, key="input_tipo_carga", disabled=(modo=="existente"))
        c_oc.text_input("Nº Ocorrência", key="input_oc", disabled=(modo=="existente"))
        c_ini.text_input("Data Início", key="input_dt_ini", disabled=(modo=="existente"), placeholder="DD/MM/YYYY")
        
        # Campo de Data Fim (Lógica Visual do Status)
        val_fim = c_fim.text_input("Data Fim", key="input_dt_fim", disabled=(modo=="existente"), placeholder="DD/MM/YYYY")
        
        status_oc_calc = "ENCERRADA" if val_fim and len(str(val_fim)) > 5 else "ABERTA"
        cor_status = "green" if status_oc_calc == "ENCERRADA" else "red"
        st.caption(f"Status Atual: :{cor_status}[**{status_oc_calc}**]")
        st.text_area("Motivo da NF Pesquisada", value=dados.get("MOTIVO_COMPLETO", ""), disabled=(modo=="existente"))

    # --- ABA 2: ITENS ---
    elif aba_selecionada == "2. Itens (NFD)":
        st.caption("Adicionar NF de Devolução (NFD) e Itens")
        if modo == "novo":
            st.markdown("### 📄 Documento da NFD (Capa)")
            col_nfd_doc1, col_nfd_doc2 = st.columns([1, 2])
            nfd_numero = col_nfd_doc1.text_input("Número da NFD (Capa)")
            
            if st.session_state.get('cache_nfd_arquivo'):
                st.success("📁 Arquivo carregado na memória.")
            
            arquivo_nfd_geral = col_nfd_doc2.file_uploader("Anexar NFD (PDF/FOTO)", type=["pdf", "jpg", "png"], key="upload_geral")
            
            if arquivo_nfd_geral:
                st.session_state['cache_nfd_arquivo'] = arquivo_nfd_geral

            st.divider()
            with st.form("form_adicionar_item", clear_on_submit=False):
                st.markdown("**Adicionar Itens na Lista:**")
                i1, i2, i3, i4 = st.columns([1, 2, 1, 1])
                cod_item = i1.text_input("Cód. Item")
                desc_item = i2.text_input("Descrição")
                qtd_item = i3.number_input("Qtd", min_value=1, value=1)
                val_item = i4.number_input("Valor Unit.", min_value=0.0, format="%.2f")
                
                if st.form_submit_button("➕ Adicionar Item"):
                    if nfd_numero and cod_item:
                        total_calc = qtd_item * val_item 
                        st.session_state['lista_itens_temp'].append({
                            "NFD": nfd_numero, "CODIGO": cod_item, "DESC": desc_item,
                            "QTD": qtd_item, "VALOR": val_item, "VALOR_TOTAL": total_calc
                        })
                        st.success("Adicionado!") 
                    else: st.warning("Preencha NFD e Código.")
        
        if len(st.session_state['lista_itens_temp']) > 0:
            st.markdown("#### Itens Adicionados:")
            df_view = pd.DataFrame(st.session_state['lista_itens_temp'])
            df_view.insert(0, "Excluir", False)
            df_edited = st.data_editor(df_view, column_config={"Excluir": st.column_config.CheckboxColumn(default=False)}, disabled=["NFD", "CODIGO", "DESC", "QTD", "VALOR", "VALOR_TOTAL"], hide_index=False, use_container_width=True, key="editor_itens_temp")
            if st.button("🗑️ Excluir Selecionados", type="secondary"):
                indices_manter = df_edited[df_edited["Excluir"] == False].index.tolist()
                st.session_state['lista_itens_temp'] = [st.session_state['lista_itens_temp'][i] for i in indices_manter]
                st.rerun()

    # --- BOTÃO SALVAR (GLOBAL - LÊ DO CACHE) ---
    st.divider()
    if modo == "novo":
        if st.button("💾 CONCLUIR E GERAR PROCESSO", type="primary", use_container_width=True):
            if not st.session_state['lista_itens_temp']:
                st.warning("⚠️ Adicione itens antes de salvar!")
            else:
                with st.spinner("Salvando..."):
                    
                    link_nfd_doc = ""
                    arquivo_final = st.session_state.get('cache_nfd_arquivo')
                    if arquivo_final:
                        bytes_do_arquivo = arquivo_final.read()
                        nome_arquivo = f"NFD_{dados.get('NF')}_{uuid.uuid4()}"
                        link_nfd_doc = upload_bytes_cloudinary(bytes_do_arquivo, nome_arquivo)

                    # Recupera Tudo do Cofre
                    v_veiculo = st.session_state.get("cache_veiculo", "")
                    v_tip_veiculo = st.session_state.get("cache_tip_veiculo", "")
                    v_motorista = st.session_state.get("cache_motorista", "")
                    v_oc = st.session_state.get("cache_oc", "")
                    v_dt_ini = st.session_state.get("cache_dt_ini", "")
                    v_dt_fim = st.session_state.get("cache_dt_fim", "")
                    v_local = st.session_state.get("cache_local_atual", "") # Pega Local Atual
                    v_destino = st.session_state.get("cache_local_destino", "") # Pega Destino
                    
                    v_tipo_carga = st.session_state.get("cache_tipo_carga", "DIRETA")
                    v_ordem = st.session_state.get("cache_ordem", "") 
                    
                    dt_dev_obj = st.session_state.get("cache_data_devolucao")
                    dt_dev_str = dt_dev_obj.strftime("%d/%m/%Y") if dt_dev_obj else ""
                    v_status_oc = "ENCERRADA" if v_dt_fim and len(str(v_dt_fim)) > 5 else "ABERTA"
                    v_prazo_txt, _ = calcular_prazo_alerta(dados.get("DATA_EMISSAO"))

                    pacote_salvar = {
                        "NF": dados.get("NF"), 
                        "CTE": dados.get("CTE"),
                        "DATA_EMISSAO": dados.get("DATA_EMISSAO"),
                        "DATA_DEVOLUCAO_CTE": dt_dev_str,
                        "VEICULO": v_veiculo,
                        "TIPO_VEICULO": v_tip_veiculo,
                        "MOTORISTA": v_motorista,
                        "OC": v_oc,
                        "ORDEM_DE_CARGA": v_ordem,
                        "DATA_INICIO": v_dt_ini,
                        "DATA_FIM": v_dt_fim,
                        "STATUS_OC": v_status_oc,
                        "PRAZO": v_prazo_txt,
                        "TIPO_CARGA": v_tipo_carga,
                        "LOCAL": v_local, # Mapeia Local Atual
                        "LOCAL_DESTINO": v_destino, # Mapeia Local Destino
                        "MOTIVO": dados.get("MOTIVO_COMPLETO"),
                        "RESPONSAVEL": st.session_state.get("usuario", "anonimo"),
                        "LINK_NFD": link_nfd_doc 
                    }
                    
                    sucesso, id_gerado = salvar_novo_processo(pacote_salvar)
                    
                    if sucesso:
                        itens_finais = []
                        for item in st.session_state['lista_itens_temp']:
                            
                            # --- LIMPEZA RADICAL ---
                            # 1. Quantidade: Converte para float primeiro (pra garantir) e depois INT
                            # Isso remove o .0 matematicamente, sem virar texto
                            try:
                                qtd_raw = int(float(item["QTD"])) 
                            except:
                                qtd_raw = 0
                            
                            # 2. Valores: Converte para FLOAT puro
                            try:
                                val_unit_raw = float(item["VALOR"])
                            except:
                                val_unit_raw = 0.0
                                
                            # 3. Recálculo Matemático
                            val_total_raw = round(qtd_raw * val_unit_raw, 2)

                            itens_finais.append({
                                "NUMERO_NFD": str(item["NFD"]), 
                                "COD_ITEM": str(item["CODIGO"]), 
                                "DESCRICAO": str(item["DESC"]),
                                
                                # ✅ AQUI ESTÁ O SEGREDO: Enviar como NÚMERO, não Texto
                                "QTD": qtd_raw,            # Vai chegar como 15 (número)
                                "VALOR_UNIT": val_unit_raw, # Vai chegar como 100.5 (número)
                                "VALOR_TOTAL": val_total_raw # Vai chegar como 1507.5 (número)
                            })
                        
                        salvar_itens_lote(id_gerado, itens_finais)
                        st.success(f"✅ Processo {id_gerado} Salvo com Documento!")
                        
                        # Limpa tudo
                        st.session_state['dados_encontrados'] = {}
                        st.session_state['lista_itens_temp'] = []
                        st.session_state['cache_nfd_arquivo'] = None
                        
                        keys_clean = [
                            'input_veiculo', 'cache_veiculo',
                            'input_tip_veiculo', 'cache_tip_veiculo',
                            'input_motorista', 'cache_motorista',
                            'input_oc', 'cache_oc',
                            'input_dt_ini', 'cache_dt_ini',
                            'input_dt_fim', 'cache_dt_fim',
                            'input_tipo_carga', 'cache_tipo_carga',
                            'input_ordem_de_carga', 'cache_ordem',
                            'input_data_devolucao', 'cache_data_devolucao',
                            'input_local_atual', 'cache_local_atual',
                            'input_local_destino', 'cache_local_destino',
                            'upload_geral'
                        ]
                        for k in keys_clean: 
                            if k in st.session_state: del st.session_state[k]
                        
                        st.rerun()