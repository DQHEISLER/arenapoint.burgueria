import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Sistema Estável", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO DE LEITURA COM CACHE (EVITA ERRO 429 E CORRIGE SOMA) ---
@st.cache_data(ttl=10)
def get_data():
    try:
        df = conn.read(worksheet="Sheet1")
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])
        
        # CORREÇÃO CRÍTICA: Garantir que datas e preços sejam números/datas reais para a soma funcionar
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        df['Preço'] = pd.to_numeric(df['Preço'], errors='coerce').fillna(0.0)
        df['Comanda'] = pd.to_numeric(df['Comanda'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"❌ ERRO DE CONEXÃO: {e}")
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
    proxima_comanda = int(df_vendas_atual['Comanda'].max() or 0) + 1

    st.title("🍔 Arena Point - Caixa")
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("📝 Dados do Pedido")
        st.session_state.nome_cliente = st.text_input("Nome do Cliente:", value=st.session_state.nome_cliente, placeholder="Ex: Diego")

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
        
        obs = st.text_input("📝 Personalizar (Ex: Sem cebola / + Bacon):", placeholder="Opcional")
        
        if st.button("➕ Adicionar Item", use_container_width=True):
            cliente_final = st.session_state.nome_cliente if st.session_state.nome_cliente else "Cliente Avulso"
            nome_final_item = f"{item_nome} ({obs})" if obs else item_nome
            
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda,
                "Nome": cliente_final,
                "Data": datetime.now(), # Salva como objeto de data real
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
                with st.spinner('Salvando no Google Sheets...'):
                    df_online = conn.read(worksheet="Sheet1")
                    df_final = pd.concat([df_online, df_cart], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=df_final)
                    st.session_state.carrinho = []
                    st.session_state.nome_cliente = ""
                    st.cache_data.clear() # Limpa o cache para atualizar faturamento na hora
                    st.success("Pedido salvo!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("Adicione itens para começar.")

# --- ABA DE RELATÓRIOS (COM SOMA CORRIGIDA) ---
with tab_relatorios:
    st.title("📊 Relatórios Financeiros")
    if st.button("🔄 Sincronizar"):
        st.cache_data.clear()
        st.rerun()

    df_vendas = get_data()
    if not df_vendas.empty:
        agora = datetime.now()
        hoje = agora.date()
        
        # Filtros de data para faturamento
        df_hoje = df_vendas[df_vendas['Data'].dt.date == hoje]
        df_mes = df_vendas[(df_vendas['Data'].dt.month == agora.month) & (df_vendas['Data'].dt.year == agora.year)]
        
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Faturamento Hoje", f"R$ {float(df_hoje['Preço'].sum()):.2f}")
        m2.metric("🗓️ Faturamento Mensal", f"R$ {float(df_mes['Preço'].sum()):.2f}")
        m3.metric("📦 Pedidos Hoje", len(df_hoje['Comanda'].unique()))
        
        st.divider()
        st.subheader("📂 Últimas Comandas")
        ids = sorted(df_vendas['Comanda'].unique(), reverse=True)[:15]
        for id_c in ids:
            detalhe = df_vendas[df_vendas['Comanda'] == id_c]
            total_c = detalhe['Preço'].sum()
            nome_cli = detalhe['Nome'].iloc[0] if not pd.isna(detalhe['Nome'].iloc[0]) else "Avulso"
            with st.expander(f"📦 Comanda #{int(id_c)} - {nome_cli} | Total: R$ {total_c:.2f}"):
                st.table(detalhe[["Item", "Preço"]])
                st.write(f"**Valor Final: R$ {total_c:.2f}**")

with tab_config:
    st.title("⚙️ Ajustes")
    st.subheader("🏁 Turno")
    if st.button("🛑 FECHAR TURNO AGORA", type="secondary"):
        st.warning("Turno encerrado para conferência.")
        st.balloons()
    
    st.divider()
    st.subheader("🛠️ Cancelar Itens")
    busca_c = st.number_input("Número da comanda para editar:", min_value=1, step=1)
    df_db = get_data()
    if not df_db.empty:
        itens = df_db[df_db['Comanda'] == busca_c]
        if not itens.empty:
            for idx, row in itens.iterrows():
                ca, cb, cc = st.columns([3, 1, 1])
                ca.write(row['Item'])
                cb.write(f"R$ {row['Preço']:.2f}")
                if cc.button("❌ Remover", key=f"ajuste_{idx}"):
                    df_real = conn.read(worksheet="Sheet1")
                    df_up = df_real.drop(idx)
                    conn.update(worksheet="Sheet1", data=df_up)
                    st.cache_data.clear()
                    st.rerun()
