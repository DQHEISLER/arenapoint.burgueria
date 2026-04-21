import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Sistema de Comandas", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ESTADOS DA SESSÃO ---
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []
if 'numero_comanda' not in st.session_state:
    # Tenta descobrir o último número de comanda na planilha
    try:
        df_temp = conn.read(worksheet="Sheet1")
        st.session_state.numero_comanda = int(df_temp['Comanda'].max()) + 1
    except:
        st.session_state.numero_comanda = 1

# --- CARDÁPIO REAL (BASEADO NA IMAGEM) ---
cardapio = {
    "HAMBÚRGUER": {
        "🍔 Simples": 15.00,
        "🍔 Duplo": 20.00,
        "🍔 Triplo": 26.00
    },
    "ESPETOS": {
        "🍢 Carne": 8.00,
        "🍢 Frango": 8.00
    },
    "BEBIDAS": {
        "🥤 Água com Gás": 4.00,
        "🥤 Refrigerante Lata": 5.00,
        "🥤 Refrigerante 1 Litro": 8.00,
        "🥤 Refrigerante 2 Litros": 18.00
    }
}

st.title("🍔 Arena Point - Gestão de Comandas")

# --- ÁREA DE VENDAS ---
col_menu, col_carrinho = st.columns([1, 1])

with col_menu:
    st.subheader("Menu")
    categoria = st.radio("Categoria:", list(cardapio.keys()))
    item_nome = st.selectbox("Produto:", list(cardapio[categoria].keys()))
    
    if st.button("➕ Adicionar ao Pedido", use_container_width=True):
        st.session_state.carrinho.append({
            "Comanda": st.session_state.numero_comanda,
            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Item": item_nome,
            "Preço": cardapio[categoria][item_nome]
        })
        st.toast(f"{item_nome} adicionado!")

with col_carrinho:
    st.subheader(f"📋 Comanda Atual: #{st.session_state.numero_comanda}")
    if st.session_state.carrinho:
        df_c = pd.DataFrame(st.session_state.carrinho)
        st.dataframe(df_c[["Item", "Preço"]], use_container_width=True)
        
        total = df_c["Preço"].sum()
        st.markdown(f"### Total: R$ {total:.2f}")
        
        if st.button("✅ Finalizar e Enviar para Nuvem", type="primary", use_container_width=True):
            try:
                # 1. Lê banco de dados existente
                try:
                    df_antigo = conn.read(worksheet="Sheet1")
                except:
                    df_antigo = pd.DataFrame(columns=["Comanda", "Data", "Item", "Preço"])
                
                # 2. Concatena (Append)
                df_novo = pd.DataFrame(st.session_state.carrinho)
                df_final = pd.concat([df_antigo, df_novo], ignore_index=True)
                
                # 3. Salva
                conn.update(worksheet="Sheet1", data=df_final)
                
                st.success(f"Pedido #{st.session_state.numero_comanda} salvo!")
                st.session_state.carrinho = []
                st.session_state.numero_comanda += 1
                st.rerun()
            except Exception as e:
                st.error("Erro na conexão. Verifique os Secrets e se a aba chama 'Sheet1'.")

st.divider()

# --- HISTÓRICO ESTILO IFOOD ---
st.header("📂 Histórico de Pedidos (Comandas)")

try:
    df_vendas = conn.read(worksheet="Sheet1")
    if not df_vendas.empty:
        # Agrupar por comanda para mostrar como o iFood
        comandas_ids = df_vendas['Comanda'].unique()[::-1] # Do mais novo para o mais antigo
        
        for id_c in comandas_ids:
            with st.expander(f"📦 Pedido #{id_c}"):
                pedido_detalhe = df_vendas[df_vendas['Comanda'] == id_c]
                data_pedido = pedido_detalhe['Data'].iloc[0]
                total_pedido = pedido_detalhe['Preço'].sum()
                
                st.write(f"**Data:** {data_pedido}")
                st.table(pedido_detalhe[["Item", "Preço"]])
                st.write(f"**Valor da Comanda:** R$ {total_pedido:.2f}")
    else:
        st.info("Nenhum pedido realizado ainda.")
except:
    st.info("Aguardando sincronização com a planilha.")
