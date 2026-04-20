import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Burger Pay Pro", page_icon="🍔", layout="centered")

# --- CORREÇÃO DO ERRO AQUI ---
# Mudamos 'unsafe_all_of_markdown' para 'unsafe_allow_html'
st.markdown("""
    <style>
    .main { text-align: center; }
    .stButton>button { 
        width: 100%; 
        border-radius: 10px; 
        height: 3.5em; 
        background-color: #2c3e50;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🍔 Burger System")
st.caption("Gestão de Vendas e Caixa")

# --- LÓGICA DE MEMÓRIA ---
if 'faturamento' not in st.session_state:
    st.session_state.faturamento = 0.0
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- SIDEBAR (Configurações) ---
with st.sidebar:
    st.header("⚙️ Administração")
    novo_total = st.number_input("Valor em Caixa (R$)", min_value=0.0, value=st.session_state.faturamento)
    if st.button("Atualizar Saldo"):
        st.session_state.faturamento = novo_total
        st.success("Saldo atualizado!")

    st.divider()
    if st.button("🚨 Zerar Caixa"):
        st.session_state.faturamento = 0.0
        st.session_state.carrinho = []
        st.rerun()

# --- ÁREA DE VENDAS ---
cardapio = {
    "Classic Burger": 25.0, 
    "Cheese Bacon": 32.0,
    "Picanha Monster": 48.0, 
    "Batata Frita": 15.0, 
    "Refrigerante": 8.0
}

st.subheader("Menu")
cols = st.columns(2)
for i, (nome, preco) in enumerate(cardapio.items()):
    with cols[i % 2]:
        if st.button(f"{nome}\nR$ {preco:.2f}", key=nome):
            st.session_state.carrinho.append({"Item": nome, "Preço": preco})

st.divider()

# --- CARRINHO E FINALIZAÇÃO ---
if st.session_state.carrinho:
    st.subheader("🛒 Pedido Atual")
    df_pedido = pd.DataFrame(st.session_state.carrinho)
    st.table(df_pedido)
    
    total_venda = df_pedido["Preço"].sum()
    
    if st.button(f"Confirmar Pagamento: R$ {total_venda:.2f}", type="primary"):
        st.session_state.faturamento += total_venda
        st.session_state.carrinho = []
        st.balloons()
        st.success("Venda Finalizada!")
        st.rerun()
    
    if st.button("Cancelar Pedido"):
        st.session_state.carrinho = []
        st.rerun()

# --- RESUMO FINANCEIRO ---
st.divider()
st.metric("Faturamento Acumulado", f"R$ {st.session_state.faturamento:.2f}")