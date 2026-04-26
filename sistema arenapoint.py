import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Gestão Total", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO DE LEITURA COM CACHE ---
@st.cache_data(ttl=10)
def get_data_cached():
    try:
        df = conn.read(worksheet="Sheet1")
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])
        
        # CORREÇÃO CRÍTICA: Garantir que datas e preços sejam números/datas reais
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        df['Preço'] = pd.to_numeric(df['Preço'], errors='coerce').fillna(0.0)
        df['Comanda'] = pd.to_numeric(df['Comanda'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"⚠️ Erro ao acessar dados: {e}")
        return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- INTERFACE ---
tab_vendas, tab_relatorios, tab_config = st.tabs(["🛒 Nova Venda", "📊 Financeiro e Turno", "⚙️ Ajustes"])

# --- ABA DE VENDAS ---
with tab_vendas:
    df_vendas_atual = get_data_cached()
    proxima_comanda = int(df_vendas_atual['Comanda'].max() or 0) + 1

    st.title("🍔 Arena Point - Caixa")
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("📝 Novo Pedido")
        nome_cliente = st.text_input("Cliente:", key="input_nome")
        
        st.divider()
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
        
        obs = st.text_input("📝 Personalizar:", key="input_obs")
        
        if st.button("➕ Adicionar ao Carrinho", use_container_width=True):
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda,
                "Nome": nome_cliente if nome_cliente else "Avulso",
                "Data": datetime.now(),
                "Item": f"{item_nome} ({obs})" if obs else item_nome,
                "Preço": float(preco)
            })
            st.rerun()

    with col2:
        st.subheader(f"📋 Comanda #{proxima_comanda}")
        if st.session_state.carrinho:
            df_c = pd.DataFrame(st.session_state.carrinho)
            for i, row in df_c.iterrows():
                ci, cp, cb = st.columns([3, 1, 1])
                ci.write(row['Item'])
                cp.write(f"R$ {row['Preço']:.2f}")
                if cb.button("🗑️", key=f"del_{i}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()
            
            st.divider()
            total_venda = df_c['Preço'].sum()
            st.write(f"### Total: R$ {total_venda:.2f}")
            
            if st.button("✅ FINALIZAR E LANÇAR", type="primary", use_container_width=True):
                with st.spinner('Lançando...'):
                    df_online = conn.read(worksheet="Sheet1")
                    df_final = pd.concat([df_online, df_c], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=df_final)
                    st.session_state.carrinho = []
                    st.cache_data.clear() 
                    st.success("Lançado com sucesso!")
                    time.sleep(1)
                    st.rerun()

# --- ABA DE RELATÓRIOS ---
with tab_relatorios:
    st.title("📊 Gestão Financeira")
    
    if st.button("🔄 Sincronizar Dados"):
        st.cache_data.clear()
        st.rerun()

    df_rel = get_data_cached()
    
    if not df_rel.empty:
        agora = datetime.now()
        hoje = agora.date()
        
        # Filtros de tempo corrigidos
        df_hoje = df_rel[df_rel['Data'].dt.date == hoje]
        df_mes = df_rel[(df_rel['Data'].dt.month == agora.month) & (df_rel['Data'].dt.year == agora.year)]
        
        m1, m2, m3 = st.columns(3)
        # Somas formatadas explicitamente como float
        m1.metric("💰 Faturamento Hoje", f"R$ {float(df_hoje['Preço'].sum()):.2f}")
        m2.metric("🗓️ Faturamento Mensal", f"R$ {float(df_mes['Preço'].sum()):.2f}")
        m3.metric("📦 Pedidos Hoje", len(df_hoje['Comanda'].unique()))
        
        st.divider()
        
        st.subheader("🏁 Turno")
        if st.button("🛑 FECHAR TURNO AGORA", type="secondary"):
            st.warning("Turno encerrado para conferência.")
            st.balloons()

        st.divider()
        st.subheader("📂 Histórico de Comandas")
        ids = sorted(df_rel['Comanda'].unique(), reverse=True)[:15]
        for id_c in ids:
            det = df_rel[df_rel['Comanda'] == id_c]
            total_c = det['Preço'].sum()
            nome_c = det['Nome'].iloc[0] if not pd.isna(det['Nome'].iloc[0]) else "Avulso"
            with st.expander(f"📦 Comanda #{int(id_c)} - {nome_c} | Total: R$ {total_c:.2f}"):
                st.table(det[["Item", "Preço"]])

# --- ABA DE AJUSTES ---
with tab_config:
    st.title("⚙️ Ajustes")
    busca_c = st.number_input("Corrigir Comanda nº:", min_value=1, step=1)
    
    df_db = get_data_cached()
    if not df_db.empty:
        itens = df_db[df_db['Comanda'] == busca_c]
        if not itens.empty:
            for idx, row in itens.iterrows():
                ca, cb, cc = st.columns([3, 1, 1])
                ca.write(row['Item'])
                cb.write(f"R$ {row['Preço']:.2f}")
                if cc.button("❌ Remover Item", key=f"ajuste_{idx}"):
                    df_real = conn.read(worksheet="Sheet1")
                    df_up = df_real.drop(idx)
                    conn.update(worksheet="Sheet1", data=df_up)
                    st.cache_data.clear()
                    st.rerun()
