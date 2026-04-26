import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Sistema Estável", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO DE LEITURA COM CACHE ---
@st.cache_data(ttl=5) # Reduzi para 5 segundos para ser mais rápido
def get_data():
    try:
        # Lendo sem cache inicial para garantir que pegamos o que está lá
        df = conn.read(worksheet="Sheet1", ttl=0)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])
        
        # --- LIMPEZA DE DADOS CRÍTICA ---
        # 1. Converte Data e remove informações de fuso horário (evita erro de comparação)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        
        # 2. Garante que Preço é número (float) e remove erros
        df['Preço'] = pd.to_numeric(df['Preço'], errors='coerce').fillna(0.0)
        
        # 3. Garante que Comanda é número inteiro
        df['Comanda'] = pd.to_numeric(df['Comanda'], errors='coerce').fillna(0)
        
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
        
        obs = st.text_input("📝 Personalizar:", placeholder="Opcional")
        
        if st.button("➕ Adicionar Item", use_container_width=True):
            cliente_final = st.session_state.nome_cliente if st.session_state.nome_cliente else "Cliente Avulso"
            nome_final_item = f"{item_nome} ({obs})" if obs else item_nome
            
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda,
                "Nome": cliente_final,
                "Data": datetime.now(), 
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
                    # Lendo o online para dar o append correto
                    df_online = conn.read(worksheet="Sheet1", ttl=0)
                    df_final = pd.concat([df_online, df_cart], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=df_final)
                    
                    # Limpando tudo para o próximo
                    st.session_state.carrinho = []
                    st.session_state.nome_cliente = ""
                    st.cache_data.clear() 
                    st.success("Pedido salvo!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("Adicione itens para começar.")

# --- ABA DE RELATÓRIOS (SOMA CORRIGIDA) ---
with tab_relatorios:
    st.title("📊 Relatórios Financeiros")
    
    if st.button("🔄 Sincronizar Agora"):
        st.cache_data.clear()
        st.rerun()

    df_vendas = get_data()
    
    if not df_vendas.empty:
        # 1. Pega a data de hoje sem horas (meia-noite)
        hoje_dt = pd.to_datetime(datetime.now().date())
        mes_atual = datetime.now().month
        ano_atual = datetime.now().year
        
        # 2. FILTRAGEM SEGURA
        # Filtra comparando apenas a parte da data (.dt.normalize() remove as horas do banco)
        df_hoje = df_vendas[df_vendas['Data'].dt.normalize() == hoje_dt]
        
        # Filtra o mês comparando mês e ano
        df_mes = df_vendas[
            (df_vendas['Data'].dt.month == mes_atual) & 
            (df_vendas['Data'].dt.year == ano_atual)
        ]
        
        # 3. CÁLCULO DAS MÉTRICAS
        total_hoje = df_hoje['Preço'].sum()
        total_mes = df_mes['Preço'].sum()
        qtd_pedidos_hoje = len(df_hoje['Comanda'].unique())
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("💰 Faturamento Hoje", f"R$ {total_hoje:.2f}")
        col_m2.metric("🗓️ Faturamento Mensal", f"R$ {total_mes:.2f}")
        col_m3.metric("📦 Pedidos Hoje", qtd_pedidos_hoje)
        
        st.divider()
        st.subheader("📂 Histórico de Comandas (Hoje)")
        if not df_hoje.empty:
            ids = sorted(df_hoje['Comanda'].unique(), reverse=True)
            for id_c in ids:
                detalhe = df_hoje[df_hoje['Comanda'] == id_c]
                total_c = detalhe['Preço'].sum()
                nome_cli = detalhe['Nome'].iloc[0]
                with st.expander(f"📦 Comanda #{int(id_c)} - {nome_cli} | Total: R$ {total_c:.2f}"):
                    st.table(detalhe[["Item", "Preço"]])
        else:
            st.info("Nenhuma venda realizada hoje ainda.")
    else:
        st.warning("A planilha parece estar vazia.")

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
                    # Lê o dado real para não deletar errado
                    df_real = conn.read(worksheet="Sheet1", ttl=0)
                    df_up = df_real.drop(idx)
                    conn.update(worksheet="Sheet1", data=df_up)
                    st.cache_data.clear()
                    st.rerun()
