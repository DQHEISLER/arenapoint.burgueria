import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Gestão Total", layout="wide")

# Conexão com Google Sheets (Tirando o cache para não sumir dados)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- FUNÇÃO PARA LER DADOS SEM CACHE ---
def get_data():
    try:
        # worksheet="Sheet1" deve ser o nome exato da aba no Google Sheets
        return conn.read(worksheet="Sheet1", ttl=0) 
    except:
        return pd.DataFrame(columns=["Comanda", "Data", "Item", "Preço"])

# Define o número da próxima comanda
df_vendas_atual = get_data()
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
tab_vendas, tab_relatorios = st.tabs(["🛒 Nova Venda", "📊 Relatórios e Faturamento"])

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
                
                # Salva na planilha
                conn.update(worksheet="Sheet1", data=df_final)
                
                st.success(f"Pedido #{proxima_comanda} enviado com sucesso!")
                st.session_state.carrinho = []
                st.rerun()

with tab_relatorios:
    st.title("📊 Controle de Faturamento")
    df_vendas = get_data()

    if not df_vendas.empty:
        # Tratamento de datas para engenharia de dados
        df_vendas['Data'] = pd.to_datetime(df_vendas['Data'])
        hoje = datetime.now().date()
        mes_atual = datetime.now().month
        ano_atual = datetime.now().year

        # 1. Faturamento Diário
        vendas_hoje = df_vendas[df_vendas['Data'].dt.date == hoje]
        fatur_dia = vendas_hoje['Preço'].sum()

        # 2. Faturamento Mensal
        vendas_mes = df_vendas[(df_vendas['Data'].dt.month == mes_atual) & (df_vendas['Data'].dt.year == ano_atual)]
        fatur_mes = vendas_mes['Preço'].sum()

        # Exibição de Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento Hoje", f"R$ {fatur_dia:.2f}")
        c2.metric("Faturamento Mensal", f"R$ {fatur_mes:.2f}")
        c3.metric("Total de Pedidos", len(df_vendas['Comanda'].unique()))

        st.divider()
        st.subheader("📂 Histórico por Comanda")
        
        # Mostra as comandas da mais recente para a mais antiga
        ids_reversos = sorted(df_vendas['Comanda'].unique(), reverse=True)
        for id_c in ids_reversos:
            with st.expander(f"📦 Comanda #{id_c} - Detalhes"):
                detalhe = df_vendas[df_vendas['Comanda'] == id_c]
                st.write(f"Data: {detalhe['Data'].iloc[0]}")
                st.dataframe(detalhe[["Item", "Preço"]], use_container_width=True)
                st.write(f"**Valor total desta comanda: R$ {detalhe['Preço'].sum():.2f}**")
    else:
        st.info("Nenhuma venda encontrada no banco de dados.")
