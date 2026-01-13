import streamlit as st
import pandas as pd
import plotly.express as px
from services.conexao_sheets import carregar_dados

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Estoque por Destino", page_icon="📦", layout="wide")

# CSS para cards de KPI
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 26px;
        color: #00B17C;
    }
    div[data-testid="stMetricLabel"] {
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNÇÕES UTILITÁRIAS (TRITURADOR DE NÚMEROS)
# ==============================================================================
def converter_float(valor):
    """Garante que R$ 1.000,00 vire 1000.00 float puro"""
    if pd.isna(valor) or valor == "": return 0.0
    if isinstance(valor, (float, int)): return float(valor)
    
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    # Lógica BR: Se tem vírgula no final (100,50), remove ponto milhar e troca vírgula
    if "," in v[-3:]: 
        v = v.replace(".", "").replace(",", ".")
    # Lógica US: Se tem ponto no final (100.50), remove vírgula milhar
    elif "." in v[-3:]:
        v = v.replace(",", "")
    
    try:
        return float(v)
    except:
        return 0.0

def carregar_dados_consolidados():
    """
    Faz o JOIN entre Processos (Capa) e Itens (Detalhe)
    """
    with st.spinner("Cruzando dados de Processos e Itens..."):
        # 1. Carrega as duas tabelas
        df_processos = carregar_dados("REGISTRO_DEVOLUCOES")
        df_itens = carregar_dados("ITENS_DEVOLUCAO")

        if df_processos.empty or df_itens.empty:
            return pd.DataFrame()

        # 2. Garante que as chaves de ligação sejam strings limpas
        # Ajuste o nome da coluna de ID conforme está na sua planilha (ID_PROCESSO ou ID)
        col_id_proc = "ID_PROCESSO" # Nome na aba de Processos
        col_id_item = "ID_PROCESSO" # Nome na aba de Itens (FK)
        
        # Normaliza ID para texto para evitar erro de int vs str
        df_processos[col_id_proc] = df_processos[col_id_proc].astype(str).str.strip()
        df_itens[col_id_item] = df_itens[col_id_item].astype(str).str.strip()

        # 3. Tratamento Numérico nos Itens (Blindagem)
        if "VALOR_TOTAL" in df_itens.columns:
            df_itens["VALOR_TOTAL_FLOAT"] = df_itens["VALOR_TOTAL"].apply(converter_float)
        else:
            df_itens["VALOR_TOTAL_FLOAT"] = 0.0
            
        if "QTD" in df_itens.columns:
            df_itens["QTD_FLOAT"] = df_itens["QTD"].apply(converter_float)
        else:
             df_itens["QTD_FLOAT"] = 0.0

        # 4. O JOIN MÁGICO (Merge)
        # Trazemos o LOCAL_DESTINO e a NF da capa para dentro de cada item
        cols_capa = [col_id_proc, "LOCAL_DESTINO", "NF", "VEICULO", "DATA_EMISSAO"]
        
        # Filtra colunas que realmente existem para não dar erro
        cols_existentes = [c for c in cols_capa if c in df_processos.columns]
        
        df_completo = pd.merge(
            df_itens, 
            df_processos[cols_existentes], 
            left_on=col_id_item, 
            right_on=col_id_proc, 
            how="inner" # Só traz itens que têm processo pai
        )
        
        return df_completo

# ==============================================================================
# INTERFACE
# ==============================================================================
st.title("📦 Controle de Estoque por Destino")
st.markdown("Visão consolidada de produtos aguardando movimentação ou tratativa.")

df = carregar_dados_consolidados()

if df.empty:
    st.warning("📭 Nenhum dado encontrado ou erro na conexão das tabelas.")
else:
    # --- FILTROS LATERAIS ---
    with st.sidebar:
        st.header("Filtros")
        
        # Filtro de Local Destino
        locais_disponiveis = df["LOCAL_DESTINO"].dropna().unique().tolist()
        # Remove vazios e ordena
        locais_disponiveis = sorted([l for l in locais_disponiveis if str(l).strip() != ""])
        
        local_selecionado = st.selectbox(
            "📍 Selecione o Destino", 
            ["Todos"] + locais_disponiveis
        )
        
        # Filtro de NF (Opcional)
        nf_filtro = st.text_input("Filtrar por NF")

    # --- APLICAÇÃO DOS FILTROS ---
    df_filtrado = df.copy()
    
    if local_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["LOCAL_DESTINO"] == local_selecionado]
        
    if nf_filtro:
        df_filtrado = df_filtrado[df_filtrado["NF"].astype(str).str.contains(nf_filtro, na=False)]

    # --- KPIS (CARTÕES) ---
    col1, col2, col3 = st.columns(3)
    
    qtd_total = df_filtrado["QTD_FLOAT"].sum()
    valor_total = df_filtrado["VALOR_TOTAL_FLOAT"].sum()
    processos_unicos = df_filtrado["ID_PROCESSO"].nunique()
    
    col1.metric("📦 Volume Total (Qtd)", f"{int(qtd_total)}")
    col2.metric("💰 Valor em Mercadoria", f"R$ {valor_total:,.2f}")
    col3.metric("🚛 Processos/NFs Envolvidos", f"{processos_unicos}")
    
    st.divider()

    # --- TIER LIST (GRÁFICO) E TABELA ---
    c_graf, c_tab = st.columns([1, 1.5])
    
    with c_graf:
        st.subheader("🔥 Tier List: Itens de Maior Valor")
        
        # Agrupa por produto para somar caso tenha o mesmo item em NFs diferentes
        if not df_filtrado.empty:
            df_tier = df_filtrado.groupby(["DESCRICAO", "NF"])["VALOR_TOTAL_FLOAT"].sum().reset_index()
            df_tier = df_tier.sort_values(by="VALOR_TOTAL_FLOAT", ascending=False).head(10)
            
            # Gráfico de Barras Horizontal
            fig = px.bar(
                df_tier, 
                x="VALOR_TOTAL_FLOAT", 
                y="DESCRICAO", 
                orientation='h',
                text_auto='.2s',
                color="VALOR_TOTAL_FLOAT",
                color_continuous_scale="Reds",
                hover_data=["NF"],
                title="Top 10 Itens (Valor R$)"
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para o gráfico.")

    with c_tab:
        st.subheader("📋 Detalhamento dos Itens")
        
        # Seleciona colunas bonitas para exibir
        cols_view = ["ID_PROCESSO", "NF", "COD_ITEM", "DESCRICAO", "QTD", "VALOR_TOTAL", "LOCAL_DESTINO"]
        # Filtra só as que existem (pra não dar erro se mudar nome no futuro)
        cols_final = [c for c in cols_view if c in df_filtrado.columns]
        
        st.dataframe(
            df_filtrado[cols_final], 
            use_container_width=True, 
            hide_index=True,
            height=400
        )