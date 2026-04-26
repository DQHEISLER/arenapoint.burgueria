import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Sistema Estável", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO DE LEITURA COM LIMPEZA PROFUNDA ---
@st.cache_data(ttl=2) 
def get_data():
    try:
        # Lendo dados brutos
        df = conn.read(worksheet="Sheet1", ttl=0)
        
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])
        
        # --- PADRONIZAÇÃO TOTAL ---
        # 1. Preço: Garante que é número para somar
        df['Preço'] = pd.to_numeric(df['Preço'], errors='coerce').fillna(0.0)
        
        # 2. Comanda: Garante que é número inteiro
        df['Comanda'] = pd.to_numeric(df['Comanda'], errors='coerce').fillna(0).astype(int)
        
        # 3. Data: Converte para datetime e cria uma coluna de texto simples 'Data_Texto' (AAAA-MM-DD)
        # Isso evita erros de fuso horário na hora de somar o faturamento
        df['Data_DT'] = pd.to_datetime(df['Data'], errors='coerce')
        df['Data_Texto'] = df['Data_DT'].dt.strftime('%Y-%m-%d')
        
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
        st.session_state.nome_cliente = st.text_input("Nome do Cliente:", value=st.session_state.nome_cliente)

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
        
        obs = st.text_input("📝 Personalizar (Opcional):")
        
        if st.button("➕ Adicionar Item", use_container_width=True):
            cliente_final = st.session_state.nome_cliente if st.session_state.nome_cliente else "Cliente Avulso"
            nome_final_item = f"{item_nome} ({obs})" if obs else item_nome
            
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda,
                "Nome": cliente_final,
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
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
                with st.spinner('Salvando...'):
                    df_online = conn.read(worksheet="Sheet1", ttl=0)
                    df_final = pd.concat([df_online, df_cart], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=df_final)
                    
                    st.session_state.carrinho = []
                    st.session_state.nome_cliente = ""
                    st.cache_data.clear() 
                    st.success("Salvo com sucesso!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("Carrinho vazio.")

# --- ABA DE RELATÓRIOS (SOMA CORRIGIDA POR TEXTO) ---
with tab_relatorios:
    st.title("📊 Relatórios Financeiros")
    
    if st.button("🔄 Atualizar Tudo"):
        st.cache_data.clear()
        st.rerun()

    df_vendas = get_data()
    
    if not df_vendas.empty:
        # Pega a data de hoje no formato texto AAAA-MM-DD
        hoje_texto = datetime.now().strftime('%Y-%m-%d')
        mes_atual = datetime.now().month
        ano_atual = datetime.now().year
        
        # Filtro de hoje usando a coluna de texto (evita erros de hora)
        df_hoje = df_vendas[df_vendas['Data_Texto'] == hoje_texto]
        
        # Filtro do mês
        df_mes = df_vendas[
            (df_vendas['Data_DT'].dt.month == mes_atual) & 
            (df_vendas['Data_DT'].dt.year == ano_atual)
        ]
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("💰 Faturamento Hoje", f"R$ {df_hoje['Preço'].sum():.2f}")
        col_m2.metric("🗓️ Faturamento Mensal", f"R$ {df_mes['Preço'].sum():.2f}")
        col_m3.metric("📦 Pedidos Hoje", len(df_hoje['Comanda'].unique()))
        
        st.divider()
        st.subheader("📂 Todas as Comandas")
        
        # Ordena para as mais novas aparecerem primeiro
        ids = sorted(df_vendas['Comanda'].unique(), reverse=True)
        for id_c in ids:
            detalhe = df_vendas[df_vendas['Comanda'] == id_c]
            if not detalhe.empty:
                total_c = detalhe['Preço'].sum()
                nome_cli = detalhe['Nome'].iloc[0]
                with st.expander(f"📦 Comanda #{int(id_c)} - {nome_cli} | R$ {total_c:.2f}"):
                    st.table(detalhe[["Item", "Preço"]])
    else:
        st.warning("Sem dados.")

with tab_config:
    st.title("⚙️ Ajustes")
    if st.button("🛑 FECHAR TURNO"):
        st.balloons()
    
    st.divider()
    busca_c = st.number_input("Número da comanda para excluir item:", min_value=1, step=1)
    if not df_vendas_atual.empty:
        itens = df_vendas_atual[df_vendas_atual['Comanda'] == busca_c]
        for idx, row in itens.iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(row['Item'])
            c2.write(f"R$ {row['Preço']:.2f}")
            if c3.button("❌", key=f"exc_{idx}"):
                df_real = conn.read(worksheet="Sheet1", ttl=0)
                df_up = df_real.drop(idx)
                conn.update(worksheet="Sheet1", data=df_up)
                st.cache_data.clear()
                st.rerun()
