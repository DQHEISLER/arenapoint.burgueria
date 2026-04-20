import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Arena Point Cloud", page_icon="🍔", layout="centered")

# Estilo CSS para botões grandes e organizados
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 4em; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO COM GOOGLE SHEETS
# Certifique-se de configurar o link da planilha nos Secrets do Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🍔 Arena Point - Gestão Cloud")
st.caption("Rua Rotterdam, 1624 - Rita Vieira")

# 3. LÓGICA DE MEMÓRIA (Session State)
if 'faturamento' not in st.session_state:
    st.session_state.faturamento = 0.0
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# 4. SIDEBAR (ADMINISTRAÇÃO)
with st.sidebar:
    st.header("⚙️ Administração")
    if st.button("🚨 Zerar Caixa Local"):
        st.session_state.faturamento = 0.0
        st.session_state.carrinho = []
        st.rerun()
    st.info("Nota: Isso não apaga os dados já salvos no Google Sheets.")

# 5. CARDÁPIO REAL
cardapio = {
    "HAMBÚRGUERES": {"🍔 Simples": 12.0, "🍔 Duplo": 18.0, "🍔 Triplo": 24.0},
    "ESPETOS": {"🍢 Carne": 10.0, "🍢 Frango": 10.0},
    "BEBIDAS": {"💧 Água": 4.0, "🥤 Refri Lata": 5.0, "🥤 Refri 1L": 8.0, "🥤 Refri 2L": 18.0}
}

# 6. INTERFACE DE VENDAS
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

# 7. CARRINHO E FINALIZAÇÃO (ENVIAR PARA CLOUD)
if st.session_state.carrinho:
    st.subheader("🛒 Pedido Atual")
    df_carrinho = pd.DataFrame(st.session_state.carrinho)
    st.table(df_carrinho[["Item", "Preço"]])
    total_venda = df_carrinho["Preço"].sum()
    
    if st.button(f"✅ Finalizar e Salvar na Nuvem: R$ {total_venda:.2f}", type="primary"):
        with st.spinner('Salvando no Google Sheets...'):
            try:
                # Busca dados existentes para não sobrescrever
                existing_data = conn.read()
                updated_df = pd.concat([existing_data, df_carrinho], ignore_index=True)
                
                # Atualiza a planilha no Drive
                conn.update(data=updated_df)
                
                # Atualiza faturamento local e limpa carrinho
                st.session_state.faturamento += total_venda
                st.session_state.carrinho = []
                st.balloons()
                st.success("Venda salva com sucesso no Google Sheets!")
                st.rerun()
            except Exception as e:
                st.error("Erro ao salvar na nuvem. Verifique a conexão e os Secrets.")

# 8. DASHBOARD E EXPORTAÇÃO MANUAL
st.divider()
st.metric("Faturamento do Turno", f"R$ {st.session_state.faturamento:.2f}")

# Botão de Excel para backup manual caso precise
try:
    all_data = conn.read()
    if not all_data.empty:
        st.subheader("📊 Relatório Geral")
        csv = all_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Planilha Completa (Excel/CSV)",
            data=csv,
            file_name=f'vendas_arena_{datetime.now().strftime("%d-%m-%Y")}.csv',
            mime='text/csv',
        )
except:
    pass
