import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 1. CONFIGURAÇÃO E CONEXÃO
st.set_page_config(page_title="Arena Point - Gestão Pro", page_icon="🍔", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; }
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# 2. FUNÇÕES DE APOIO
def get_data():
    try:
        return conn.read()
    except:
        return pd.DataFrame(columns=["ID", "Data", "Item", "Preço"])

# 3. INTERFACE PRINCIPAL (Abas)
tab1, tab2, tab3 = st.tabs(["🛒 Vendas", "📊 Relatórios", "⚙️ Ajustes"])

with tab1:
    st.title("🍔 Arena Point")
    
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []

    # Cardápio
    cardapio = {
        "HAMBÚRGUERES": {"🍔 Simples": 12.0, "🍔 Duplo": 18.0, "🍔 Triplo": 24.0},
        "ESPETOS": {"🍢 Carne": 10.0, "🍢 Frango": 10.0},
        "BEBIDAS": {"💧 Água": 4.0, "🥤 Refri Lata": 5.0, "🥤 Refri 1L": 8.0, "🥤 Refri 2L": 18.0}
    }

    cols_card = st.columns(2)
    with cols_card[0]:
        for categoria, itens in cardapio.items():
            st.subheader(categoria)
            for nome, preco in itens.items():
                if st.button(f"{nome} - R$ {preco:.2f}", key=f"btn_{nome}"):
                    st.session_state.carrinho.append({"Item": nome, "Preço": preco})
                    st.toast(f"{nome} no carrinho!")

    with cols_card[1]:
        st.subheader("🛒 Pedido Atual")
        if st.session_state.carrinho:
            df_atual = pd.DataFrame(st.session_state.carrinho)
            st.dataframe(df_atual, use_container_width=True)
            total = df_atual["Preço"].sum()
            
            if st.button(f"✅ Finalizar Pedido: R$ {total:.2f}", type="primary"):
                with st.spinner('Salvando...'):
                    df_total = get_data()
                    
                    # Gerar ID do Pedido (Numeração)
                    novo_id = 1 if df_total.empty else df_total["ID"].max() + 1
                    
                    # Preparar dados novos
                    novos_itens = df_atual.copy()
                    novos_itens["ID"] = novo_id
                    novos_itens["Data"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Concatenar e salvar
                    df_final = pd.concat([df_total, novos_itens], ignore_index=True)
                    conn.update(data=df_final)
                    
                    st.session_state.carrinho = []
                    st.balloons()
                    st.rerun()
        else:
            st.info("Carrinho vazio")

with tab2:
    st.title("📊 Desempenho Financeiro")
    df_vendas = get_data()
    
    if not df_vendas.empty:
        # Converter coluna de data para o formato Python
        df_vendas['Data'] = pd.to_datetime(df_vendas['Data'])
        hoje = datetime.now()
        
        # Filtros de Tempo
        vendas_hoje = df_vendas[df_vendas['Data'].dt.date == hoje.date()]
        vendas_semana = df_vendas[df_vendas['Data'] > (hoje - timedelta(days=7))]
        vendas_mes = df_vendas[df_vendas['Data'] > (hoje - timedelta(days=30))]

        # Métricas em Colunas
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento Diário", f"R$ {vendas_hoje['Preço'].sum():.2f}")
        m2.metric("Faturamento Semanal", f"R$ {vendas_semana['Preço'].sum():.2f}")
        m3.metric("Faturamento Mensal", f"R$ {vendas_mes['Preço'].sum():.2f}")

        st.divider()
        st.subheader("📋 Histórico de Pedidos Numerados")
        st.dataframe(df_vendas.sort_values(by="ID", ascending=False), use_container_width=True)
    else:
        st.warning("Nenhuma venda registrada no banco de dados.")

with tab3:
    st.title("⚙️ Ajustes do Sistema")
    st.write("Aqui você pode baixar os dados para backup ou limpar erros.")
    
    df_admin = get_data()
    if not df_admin.empty:
        csv = df_admin.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Backup Completo (CSV)", data=csv, file_name="backup_arena.csv")
        
        if st.button("🚨 Apagar ÚLTIMO pedido (Erro de digitação)"):
            ultimo_id = df_admin["ID"].max()
            df_admin = df_admin[df_admin["ID"] != ultimo_id]
            conn.update(data=df_admin)
            st.warning(f"Pedido #{ultimo_id} removido!")
            st.rerun()
