import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Gestão Total", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO DE LEITURA SEGURA ---
def get_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty and len(df.columns) < 2):
            return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])
        # Força a conversão e transforma erros/vazios em NaT
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"❌ ERRO DE CONEXÃO: {e}")
        st.stop()

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- INTERFACE ---
tab_vendas, tab_relatorios, tab_config = st.tabs(["🛒 Nova Venda", "📊 Financeiro e Turno", "⚙️ Ajustes"])

# --- ABA DE VENDAS ---
with tab_vendas:
    df_vendas_atual = get_data()
    proxima_comanda = int(pd.to_numeric(df_vendas_atual['Comanda'], errors='coerce').max() or 0) + 1

    st.title("🍔 Arena Point - Caixa")
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("📝 Novo Pedido")
        nome_cliente = st.text_input("Cliente:", placeholder="Ex: Diego")
        
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
        
        obs = st.text_input("📝 Personalizar:")
        
        if st.button("➕ Adicionar ao Carrinho", use_container_width=True):
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda,
                "Nome": nome_cliente if nome_cliente else "Avulso",
                "Data": datetime.now(), # Aqui já manda como datetime
                "Item": f"{item_nome} ({obs})" if obs else item_nome,
                "Preço": preco
            })
            st.rerun()

    with col2:
        st.subheader(f"📋 Comanda Atual #{proxima_comanda}")
        if st.session_state.carrinho:
            df_c = pd.DataFrame(st.session_state.carrinho)
            for i, row in df_c.iterrows():
                c_i, c_p, c_b = st.columns([3, 1, 1])
                c_i.write(row['Item'])
                c_p.write(f"R$ {row['Preço']:.2f}")
                if c_b.button("🗑️", key=f"venda_{i}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()
            
            st.divider()
            total_venda = df_c['Preço'].sum()
            st.write(f"### Total: R$ {total_venda:.2f}")
            
            if st.button("✅ FINALIZAR E LANÇAR", type="primary", use_container_width=True):
                with st.spinner('Salvando...'):
                    df_online = get_data()
                    df_final = pd.concat([df_online, df_c], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=df_final)
                    st.session_state.carrinho = []
                    st.success("Lançado!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("Carrinho vazio.")

# --- ABA DE RELATÓRIOS ---
with tab_relatorios:
    st.title("📊 Gestão Financeira")
    df_rel = get_data()
    
    if not df_rel.empty:
        agora = datetime.now()
        hoje = agora.date()
        mes_atual = agora.month
        ano_atual = agora.year
        
        df_hoje = df_rel[df_rel['Data'].dt.date == hoje]
        df_mes = df_rel[(df_rel['Data'].dt.month == mes_atual) & (df_rel['Data'].dt.year == ano_atual)]
        
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Faturamento Hoje", f"R$ {df_hoje['Preço'].sum():.2f}")
        m2.metric("🗓️ Faturamento Mensal", f"R$ {df_mes['Preço'].sum():.2f}")
        m3.metric("📦 Pedidos Hoje", len(df_hoje['Comanda'].unique()))
        
        st.divider()
        
        st.subheader("🏁 Finalizar Expediente")
        st.write("Ao encerrar o turno, o faturamento diário será pausado para conferência.")
        if st.button("🛑 FECHAR TURNO AGORA", type="secondary"):
            st.warning("Turno encerrado! (Os dados continuam salvos no histórico mensal).")
            st.balloons()

        st.divider()
        st.subheader("📂 Histórico Recente")
        ids = sorted(df_rel['Comanda'].unique(), reverse=True)[:10] 
        for id_c in ids:
            det = df_rel[df_rel['Comanda'] == id_c]
            
            # --- PROTEÇÃO CONTRA O ERRO 'NAT' ---
            data_val = det['Data'].iloc[0]
            if pd.isna(data_val):
                hora_str = "--:--"
            else:
                hora_str = data_val.strftime('%H:%M')
                
            nome_cli = det['Nome'].iloc[0] if not pd.isna(det['Nome'].iloc[0]) else "Avulso"
            # ------------------------------------
            
            with st.expander(f"Comanda #{int(id_c)} - {nome_cli} ({hora_str})"):
                st.table(det[["Item", "Preço"]])

# --- ABA DE AJUSTES ---
with tab_config:
    st.title("⚙️ Ajustes")
    busca_c = st.number_input("Número da comanda para corrigir/remover item:", min_value=1, step=1)
    df_db = get_data()
    
    if not df_db.empty:
        df_db['Comanda'] = pd.to_numeric(df_db['Comanda'], errors='coerce')
        itens = df_db[df_db['Comanda'] == busca_c]
        
        if not itens.empty:
            for idx, row in itens.iterrows():
                ca, cb, cc = st.columns([3, 1, 1])
                ca.write(row['Item'])
                cb.write(f"R$ {row['Preço']:.2f}")
                if cc.button("❌ Cancelar", key=f"cancel_{idx}"):
                    df_up = df_db.drop(idx)
                    conn.update(worksheet="Sheet1", data=df_up)
                    st.rerun()
