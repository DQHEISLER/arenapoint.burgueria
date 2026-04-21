import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Arena Point Cloud", page_icon="🍔", layout="centered")

# Estilo CSS
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 4em; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🍔 Arena Point - Gestão Cloud")

# --- LÓGICA DE MEMÓRIA LOCAL ---
if 'faturamento' not in st.session_state:
    st.session_state.faturamento = 0.0
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- CARDÁPIO ---
cardapio = {
    "HAMBÚRGUERES": {"🍔 Simples": 12.0, "🍔 Duplo": 18.0, "🍔 Triplo": 24.0},
    "ESPETOS": {"🍢 Carne": 10.0, "🍢 Frango": 10.0},
    "BEBIDAS": {"💧 Água": 4.0, "🥤 Refri Lata": 5.0, "🥤 Refri 1L": 8.0, "🥤 Refri 2L": 18.0}
}

# Interface de Vendas
for categoria, itens in cardapio.items():
    st.subheader(categoria)
    cols = st.columns(2)
    for i, (nome, preco) in enumerate(itens.items()):
        with cols[i % 2]:
            if st.button(f"{nome}\nR$ {preco:.2f}", key=nome):
                st.session_state.carrinho.append({
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "Item": nome, 
                    "Preço": preco
                })
                st.toast(f"{nome} adicionado!")

st.divider()

# Finalização com Tratamento de Erro Refinado
if st.session_state.carrinho:
    st.subheader("🛒 Pedido Atual")
    df_carrinho = pd.DataFrame(st.session_state.carrinho)
    st.table(df_carrinho[["Item", "Preço"]])
    total_venda = df_carrinho["Preço"].sum()
    
    if st.button(f"✅ Finalizar e Salvar: R$ {total_venda:.2f}", type="primary"):
        with st.spinner('Conectando ao Google Sheets...'):
            try:
                # Tenta ler; se falhar ou estiver vazio, cria um DataFrame novo
                try:
                    existing_data = conn.read()
                except:
                    existing_data = pd.DataFrame(columns=["Data", "Item", "Preço"])
                
                # Garante que não haja colunas nulas que quebrem o concat
                updated_df = pd.concat([existing_data, df_carrinho], ignore_index=True).dropna(how='all', axis=1)
                
                # Faz o upload
                conn.update(data=updated_df)
                
                st.session_state.faturamento += total_venda
                st.session_state.carrinho = []
                st.balloons()
                st.success("Venda salva com sucesso!")
                st.rerun()
            except Exception as e:
                # Mostra o erro técnico para ajudar no debug
                st.error(f"Erro técnico: {e}")
                st.info("Verifique se a planilha está como 'Editor' para 'Qualquer pessoa com o link'.")

st.metric("Faturamento do Turno", f"R$ {st.session_state.faturamento:.2f}")
