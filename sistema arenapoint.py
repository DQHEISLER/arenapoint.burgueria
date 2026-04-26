import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Sistema Estável", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO DE LEITURA COM LIMPEZA PROFUNDA (VERSÃO BLINDADA) ---
@st.cache_data(ttl=2) 
def get_data():
    try:
        # Lendo dados brutos sem cache do driver para garantir novos dados
        df = conn.read(worksheet="Sheet1", ttl=0)
        
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])
        
        # --- LIMPEZA DE PREÇO (O PONTO CRÍTICO) ---
        # Converte para string primeiro para manipular, remove R$, espaços e ajusta vírgula
        if 'Preço' in df.columns:
            df['Preço'] = df['Preço'].astype(str).str.replace('R$', '', regex=False)
            df['Preço'] = df['Preço'].str.replace('.', '', regex=False) # Remove ponto de milhar
            df['Preço'] = df['Preço'].str.replace(',', '.', regex=False) # Troca vírgula por ponto
            df['Preço'] = pd.to_numeric(df['Preço'], errors='coerce').fillna(0.0)
        
        # --- LIMPEZA DE COMANDA ---
        df['Comanda'] = pd.to_numeric(df['Comanda'], errors='coerce').fillna(0).astype(int)
        
        # --- LIMPEZA DE DATA ---
        # Converte para datetime garantindo que erros virem NaT
        df['Data_DT'] = pd.to_datetime(df['Data'], errors='coerce')
        # Cria coluna de texto puro para comparação de faturamento diário
        df['Data_Texto'] = df['Data_DT'].dt.strftime('%Y-%m-%d')
        
        return df
    except Exception as e:
        st.error(f"❌ ERRO AO PROCESSAR DADOS: {e}")
        return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []
if 'nome_cliente' not in st.session_state:
    st.session_state.nome_cliente = ""

# --- INTERFACE POR ABAS ---
tab_vendas, tab_relatorios, tab_config = st.tabs(["🛒 Nova Venda", "📊 Relatórios", "⚙️ Ajustes e Config"])

with tab_vendas:
    df_vendas_atual = get_data()
    # Pega o maior número de comanda para sugerir o próximo
    proxima_comanda = int(df_vendas_atual['Comanda'].max() if not df_vendas_atual.empty else 0) + 1

    st.title("🍔 Arena Point - Caixa")
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("📝 Dados do Pedido")
        st.session_state.nome_cliente = st.text_input("Nome do Cliente:", value=st.session_state.nome_cliente)

        st.divider()
        st.subheader("🍔 Menu")
        
        cardapio = {
            "HAMBÚRGUER": {"🍔 Simples": 15.0, "🍔 Duplo": 20.0, "🍔 Triplo": 26.0},
            "ESPETOS": {"🍢 Carne": 8.0, "🍢 Frango": 8.0},
            "BEBIDAS": {"🥤 Água": 4.0, "🥤 Lata": 5.0, "🥤 1 Litro": 8.0, "🥤 2 Litros": 18.0},
            "OFERTA/SINUCA": {"🎱 Sinuca/Valor Manual": 0.0}
        }
        
        cat = st.radio("Categoria", list(cardapio.keys()))
        
        if cat == "OFERTA/SINUCA":
            item_nome = "🎱 Oferta/Sinuca"
            preco = st.number_input("Valor (R$):", min_value=0.0, step=1.0)
        else:
            item_nome = st.selectbox("Produto", list(cardapio[cat].keys()))
            preco = cardapio[cat][item_nome]
        
        obs = st.text_input("📝 Personalizar (Opcional):")
        
        if st.button("➕ Adicionar Item", use_container_width=True):
            cliente_final = st.session_state.nome_cliente if st.session_state.nome_cliente else "Cliente Avulso"
            nome_final_item = f"{item_nome} ({obs})" if obs else item_nome
            
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda,
                "Nome": cliente_final,
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                "Item": nome_final_item,
                "Preço": float(preco)
            })
            st.toast(f"Adicionado: {nome_final_item}")
            st.rerun()

    with col2:
        st.subheader(f"📋 Comanda #{proxima_comanda}")
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            
            for i, row in df_cart.iterrows():
                c_i, c_p, c_b = st.columns([3, 1, 1])
                c_i.write(row['Item'])
                c_p.write(f"R$ {row['Preço']:.2f}")
                if c_b.button("🗑️", key=f"del_{i}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()
            
            st.divider()
            total_comanda = df_cart["Preço"].sum()
            st.write(f"### Total: R$ {total_comanda:.2f}")

            if st.button("✅ FINALIZAR E SALVAR", type="primary", use_container_width=True):
                with st.spinner('Gravando na Planilha...'):
                    # Lê o estado atual da planilha para anexar
                    df_online = conn.read(worksheet="Sheet1", ttl=0)
                    df_final = pd.concat([df_online, df_cart], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=df_final)
                    
                    # Limpa tudo
                    st.session_state.carrinho = []
                    st.session_state.nome_cliente = ""
                    st.cache_data.clear() 
                    st.success("Pedido Finalizado!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("O carrinho está vazio.")

# --- ABA DE RELATÓRIOS (CÁLCULOS REVISADOS) ---
with tab_relatorios:
    st.title("📊 Relatórios Financeiros")
    
    if st.button("🔄 Sincronizar Dados"):
        st.cache_data.clear()
        st.rerun()

    df_vendas = get_data()
    
    if not df_vendas.empty:
        # Pega data de hoje para o filtro
        hoje_ref = datetime.now().strftime('%Y-%m-%d')
        mes_ref = datetime.now().month
        ano_ref = datetime.now().year
        
        # FILTROS
        df_hoje = df_vendas[df_vendas['Data_Texto'] == hoje_ref]
        df_mes = df_vendas[(df_vendas['Data_DT'].dt.month == mes_ref) & (df_vendas['Data_DT'].dt.year == ano_ref)]
        
        # EXIBIÇÃO DOS VALORES
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Faturamento Hoje", f"R$ {df_hoje['Preço'].sum():.2f}")
        c2.metric("🗓️ Faturamento Mensal", f"R$ {df_mes['Preço'].sum():.2f}")
        c3.metric("📦 Pedidos Hoje", len(df_hoje['Comanda'].unique()))
        
        st.divider()
        st.subheader("📂 Histórico Recente de Comandas")
        
        # Ordenação decrescente (mais novos primeiro)
        ids_comandas = sorted(df_vendas['Comanda'].unique(), reverse=True)
        for id_c in ids_comandas:
            dados_comanda = df_vendas[df_vendas['Comanda'] == id_c]
            if not dados_comanda.empty:
                total_da_comanda = dados_comanda['Preço'].sum()
                nome_do_cliente = dados_comanda['Nome'].iloc[0]
                with st.expander(f"Comanda #{int(id_c)} - {nome_do_cliente} | Total: R$ {total_da_comanda:.2f}"):
                    st.table(dados_comanda[["Item", "Preço"]])
    else:
        st.warning("Nenhum dado encontrado na planilha.")

with tab_config:
    st.title("⚙️ Ajustes e Gerenciamento")
    if st.button("🛑 FECHAR TURNO"):
        st.balloons()
        st.info("Turno sinalizado como encerrado.")
    
    st.divider()
    st.subheader("🛠️ Excluir Itens Lançados")
    comanda_ajuste = st.number_input("Digite o número da comanda:", min_value=1, step=1)
    
    # Busca dados atuais para exclusão
    df_ajuste = get_data()
    if not df_ajuste.empty:
        itens_ajuste = df_ajuste[df_ajuste['Comanda'] == comanda_ajuste]
        if not itens_ajuste.empty:
            for idx, row in itens_ajuste.iterrows():
                col_a, col_b, col_c = st.columns([3, 1, 1])
                col_a.write(row['Item'])
                col_b.write(f"R$ {row['Preço']:.2f}")
                if col_c.button("Excluir", key=f"del_db_{idx}"):
                    # Lê a planilha original
                    df_base = conn.read(worksheet="Sheet1", ttl=0)
                    # Remove pelo índice exato
                    df_nova = df_base.drop(idx)
                    conn.update(worksheet="Sheet1", data=df_nova)
                    st.cache_data.clear()
                    st.success("Item removido!")
                    st.rerun()
        else:
            st.write("Nenhum item encontrado para esta comanda.")
