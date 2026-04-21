import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Gestão Total", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO PARA LER DADOS SEM CACHE ---
def get_data():
    try:
        return conn.read(worksheet="Sheet1", ttl=0) 
    except:
        return pd.DataFrame(columns=["Comanda", "Data", "Item", "Preço"])

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

df_vendas_atual = get_data()

# Lógica para número da comanda
if not df_vendas_atual.empty:
    proxima_comanda = int(df_vendas_atual['Comanda'].max()) + 1
else:
    proxima_comanda = 1

# --- CARDÁPIO ---
cardapio = {
    "HAMBÚRGUER": {"🍔 Simples": 15.0, "🍔 Duplo": 20.0, "🍔 Triplo": 26.0},
    "ESPETOS": {"🍢 Carne": 8.0, "🍢 Frango": 8.0},
    "BEBIDAS": {"🥤 Água": 4.0, "🥤 Lata": 5.0, "🥤 1 Litro": 8.0, "🥤 2 Litros": 18.0}
}

# --- INTERFACE POR ABAS ---
tab_vendas, tab_relatorios, tab_config = st.tabs(["🛒 Nova Venda", "📊 Relatórios", "⚙️ Configurações/Reset"])

with tab_vendas:
    st.title("🍔 Arena Point - Caixa")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Menu")
        cat = st.radio("Categoria", list(cardapio.keys()))
        prod = st.selectbox("Produto", list(cardapio[cat].keys()))
        
        if st.button("➕ Adicionar Item"):
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda,
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Item": prod,
                "Preço": cardapio[cat][prod]
            })
            st.toast("Item adicionado!")

    with col2:
        st.subheader(f"📋 Comanda Atual: #{proxima_comanda}")
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            st.table(df_cart[["Item", "Preço"]])
            total_comanda = df_cart["Preço"].sum()
            st.write(f"### Total Comanda: R$ {total_comanda:.2f}")

            if st.button("✅ Finalizar Pedido", type="primary"):
                df_antigo = get_data()
                df_final = pd.concat([df_antigo, df_cart], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df_final)
                st.success(f"Pedido #{proxima_comanda} salvo!")
                st.session_state.carrinho = []
                st.rerun()

with tab_relatorios:
    st.title("📊 Controle de Faturamento")
    df_vendas = get_data()

    if not df_vendas.empty:
        df_vendas['Data'] = pd.to_datetime(df_vendas['Data'])
        hoje = datetime.now().date()
        mes_atual = datetime.now().month
        ano_atual = datetime.now().year

        fatur_dia = df_vendas[df_vendas['Data'].dt.date == hoje]['Preço'].sum()
        fatur_mes = df_vendas[(df_vendas['Data'].dt.month == mes_atual) & (df_vendas['Data'].dt.year == ano_atual)]['Preço'].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento Hoje", f"R$ {fatur_dia:.2f}")
        c2.metric("Faturamento Mensal", f"R$ {fatur_mes:.2f}")
        c3.metric("Total de Pedidos", len(df_vendas['Comanda'].unique()))

        st.divider()
        st.subheader("📂 Histórico por Comanda")
        ids_reversos = sorted(df_vendas['Comanda'].unique(), reverse=True)
        for id_c in ids_reversos:
            with st.expander(f"📦 Comanda #{id_c}"):
                detalhe = df_vendas[df_vendas['Comanda'] == id_c]
                st.write(f"Data: {detalhe['Data'].iloc[0]}")
                st.table(detalhe[["Item", "Preço"]])
                st.write(f"**Total: R$ {detalhe['Preço'].sum():.2f}**")
    else:
        st.info("Nenhuma venda encontrada.")

with tab_config:
    st.title("⚙️ Administração do Sistema")
    st.warning("Ações abaixo apagam dados da planilha do Google!")

    # RESETAR APENAS O DIA (Faturamento Diário)
    if st.button("🗑️ Resetar Faturamento de Hoje"):
        df_atual = get_data()
        if not df_atual.empty:
            df_atual['Data'] = pd.to_datetime(df_atual['Data'])
            hoje = datetime.now().date()
            # Mantém apenas o que NÃO é de hoje
            df_filtrado = df_atual[df_atual['Data'].dt.date != hoje]
            conn.update(worksheet="Sheet1", data=df_filtrado)
            st.success("Faturamento de hoje resetado!")
            st.rerun()

    st.divider()

    # LIMPAR TUDO (Zerar sistema)
    if st.button("🚨 LIMPAR TODOS OS PEDIDOS (Geral)"):
        df_vazio = pd.DataFrame(columns=["Comanda", "Data", "Item", "Preço"])
        conn.update(worksheet="Sheet1", data=df_vazio)
        st.success("Todo o histórico foi apagado!")
        st.rerun()
