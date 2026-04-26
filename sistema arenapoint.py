import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Sistema Estável", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO DE FORMATAR MOEDA ---
def formatar_moeda(valor):
    """Transforma um número (float) em string no formato R$ 00,00"""
    return f"R$ {valor:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')

# --- FUNÇÃO DE LEITURA COM LIMPEZA PROFUNDA ---
@st.cache_data(ttl=2) 
def get_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])
        
        # Limpeza de Preço
        if 'Preço' in df.columns:
            df['Preço'] = df['Preço'].astype(str).str.replace('R$', '', regex=False)
            df['Preço'] = df['Preço'].str.replace('.', '', regex=False)
            df['Preço'] = df['Preço'].str.replace(',', '.', regex=False)
            df['Preço'] = pd.to_numeric(df['Preço'], errors='coerce').fillna(0.0)
        
        # Limpeza de Comanda e Data
        df['Comanda'] = pd.to_numeric(df['Comanda'], errors='coerce').fillna(0).astype(int)
        df['Data_DT'] = pd.to_datetime(df['Data'], errors='coerce')
        df['Data_Texto'] = df['Data_DT'].dt.strftime('%Y-%m-%d')
        
        return df
    except Exception as e:
        st.error(f"❌ ERRO AO PROCESSAR DADOS: {e}")
        return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'carrinho' not in st.session_state: st.session_state.carrinho = []
if 'nome_cliente' not in st.session_state: st.session_state.nome_cliente = ""

# --- INTERFACE POR ABAS ---
tab_vendas, tab_relatorios, tab_config = st.tabs(["🛒 Nova Venda", "📊 Relatórios", "⚙️ Ajustes e Config"])

with tab_vendas:
    df_vendas_atual = get_data()
    proxima_comanda = int(df_vendas_atual['Comanda'].max() if not df_vendas_atual.empty else 0) + 1

    st.title("🍔 Arena Point - Caixa")
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("📝 Dados do Pedido")
        st.session_state.nome_cliente = st.text_input("Nome do Cliente:", value=st.session_state.nome_cliente)
        
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
            st.session_state.carrinho.append({"Comanda": proxima_comanda, "Nome": cliente_final, "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Item": f"{item_nome} ({obs})" if obs else item_nome, "Preço": float(preco)})
            st.rerun()

    with col2:
        st.subheader(f"📋 Comanda #{proxima_comanda}")
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            for i, row in df_cart.iterrows():
                c_i, c_p, c_b = st.columns([3, 1, 1])
                c_i.write(row['Item'])
                c_p.write(formatar_moeda(row['Preço']))
                if c_b.button("🗑️", key=f"del_{i}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()
            st.divider()
            st.write(f"### Total: {formatar_moeda(df_cart['Preço'].sum())}")
            if st.button("✅ FINALIZAR E SALVAR", type="primary", use_container_width=True):
                df_online = conn.read(worksheet="Sheet1", ttl=0)
                conn.update(worksheet="Sheet1", data=pd.concat([df_online, df_cart], ignore_index=True))
                st.session_state.carrinho = []; st.session_state.nome_cliente = ""; st.cache_data.clear(); st.rerun()

with tab_relatorios:
    st.title("📊 Relatórios Financeiros")
    if st.button("🔄 Sincronizar"): st.cache_data.clear(); st.rerun()
    
    df_vendas = get_data()
    if not df_vendas.empty:
        hoje_ref = datetime.now().strftime('%Y-%m-%d')
        df_hoje = df_vendas[df_vendas['Data_Texto'] == hoje_ref]
        df_mes = df_vendas[(df_vendas['Data_DT'].dt.month == datetime.now().month)]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Faturamento Hoje", formatar_moeda(df_hoje['Preço'].sum()))
        c2.metric("🗓️ Faturamento Mensal", formatar_moeda(df_mes['Preço'].sum()))
        c3.metric("📦 Pedidos Hoje", len(df_hoje['Comanda'].unique()))
        
        st.subheader("📂 Histórico de Comandas")
        for id_c in sorted(df_vendas['Comanda'].unique(), reverse=True):
            detalhe = df_vendas[df_vendas['Comanda'] == id_c]
            total_c = detalhe['Preço'].sum()
            with st.expander(f"Comanda #{int(id_c)} - {detalhe['Nome'].iloc[0]} | Total: {formatar_moeda(total_c)}"):
                df_exibir = detalhe[["Item", "Preço"]].copy()
                df_exibir["Preço"] = df_exibir["Preço"].apply(formatar_moeda)
                st.table(df_exibir)

with tab_config:
    st.title("⚙️ Ajustes")
    comanda_ajuste = st.number_input("Excluir item da comanda:", min_value=1, step=1)
    df_ajuste = get_data()
    itens_ajuste = df_ajuste[df_ajuste['Comanda'] == comanda_ajuste]
    for idx, row in itens_ajuste.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(row['Item']); c2.write(formatar_moeda(row['Preço']))
        if c3.button("❌", key=f"exc_{idx}"):
            conn.update(worksheet="Sheet1", data=conn.read(worksheet="Sheet1", ttl=0).drop(idx))
            st.cache_data.clear(); st.rerun()
