import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Sistema Oficial", layout="wide", page_icon="🍔")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE UTILIDADE ---
def formatar_moeda(valor):
    """Converte um número float para o formato string R$ 00,00"""
    try:
        return f"R$ {float(valor):,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
    except:
        return "R$ 0,00"

@st.cache_data(ttl=2) 
def get_data():
    """Lê e limpa os dados da planilha garantindo precisão matemática"""
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])
        
        if 'Preço' in df.columns:
            def limpar_valor(v):
                if isinstance(v, (int, float)):
                    return float(v)
                v = str(v).replace('R$', '').strip()
                if not v or v.lower() == 'nan': 
                    return 0.0
                if '.' in v and ',' in v:
                    v = v.replace('.', '')
                v = v.replace(',', '.')
                try:
                    return float(v)
                except:
                    return 0.0
            df['Preço'] = df['Preço'].apply(limpar_valor)
        
        df['Comanda'] = pd.to_numeric(df['Comanda'], errors='coerce').fillna(0).astype(int)
        df['Data_DT'] = pd.to_datetime(df['Data'], errors='coerce')
        df['Data_Texto'] = df['Data_DT'].dt.strftime('%Y-%m-%d')
        
        return df
    except Exception as e:
        st.error(f"❌ ERRO DE LEITURA: {e}")
        return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []
if 'nome_cliente' not in st.session_state:
    st.session_state.nome_cliente = ""

# --- INTERFACE POR ABAS ---
tab_vendas, tab_relatorios, tab_config = st.tabs(["🛒 Nova Venda", "📊 Relatórios", "⚙️ Ajustes e Config"])

# --- ABA 1: VENDAS (Sem alterações) ---
with tab_vendas:
    df_vendas_atual = get_data()
    proxima_comanda = int(df_vendas_atual['Comanda'].max() if not df_vendas_atual.empty else 0) + 1
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
        obs = st.text_input("📝 Personalizar (Opcional):", placeholder="Ex: Sem cebola")
        if st.button("➕ Adicionar Item", use_container_width=True):
            cliente_final = st.session_state.nome_cliente if st.session_state.nome_cliente else "Cliente Avulso"
            st.session_state.carrinho.append({"Comanda": proxima_comanda, "Nome": cliente_final, "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Item": f"{item_nome} ({obs})" if obs else item_nome, "Preço": float(preco)})
            st.toast(f"Adicionado: {item_nome}")
            st.rerun()
    with col2:
        st.subheader(f"📋 Comanda #{proxima_comanda}")
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            for i, row in df_cart.iterrows():
                c_i, c_p, c_b = st.columns([3, 1, 1])
                c_i.write(row['Item'])
                c_p.write(formatar_moeda(row['Preço']))
                if c_b.button("🗑️", key=f"del_{i}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()
            st.divider()
            total_cart = df_cart["Preço"].sum()
            st.write(f"### Total: {formatar_moeda(total_cart)}")
            if st.button("✅ FINALIZAR E SALVAR", type="primary", use_container_width=True):
                with st.spinner('Salvando...'):
                    df_online = conn.read(worksheet="Sheet1", ttl=0)
                    df_final = pd.concat([df_online, df_cart], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=df_final)
                    st.session_state.carrinho = []
                    st.session_state.nome_cliente = ""
                    st.cache_data.clear()
                    st.success("Pedido Salvo!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("O carrinho está vazio.")

# --- ABA 2: RELATÓRIOS (Sem alterações) ---
with tab_relatorios:
    st.title("📊 Relatórios Financeiros")
    if st.button("🔄 Sincronizar Dados"):
        st.cache_data.clear()
        st.rerun()
    df_vendas = get_data()
    if not df_vendas.empty:
        hoje_ref = datetime.now().strftime('%Y-%m-%d')
        df_hoje = df_vendas[df_vendas['Data_Texto'] == hoje_ref]
        df_mes = df_vendas[df_vendas['Data_DT'].dt.month == datetime.now().month]
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Faturamento Hoje", formatar_moeda(df_hoje['Preço'].sum()))
        c2.metric("🗓️ Faturamento Mensal", formatar_moeda(df_mes['Preço'].sum()))
        c3.metric("📦 Pedidos Hoje", len(df_hoje['Comanda'].unique()))
        st.divider()
        st.subheader("📂 Histórico de Comandas")
        ids = sorted(df_vendas['Comanda'].unique(), reverse=True)
        for id_c in ids:
            dados = df_vendas[df_vendas['Comanda'] == id_c]
            total_c = dados['Preço'].sum()
            with st.expander(f"Comanda #{int(id_c)} - {dados['Nome'].iloc[0]} | Total: {formatar_moeda(total_c)}"):
                df_tab = dados[["Item", "Preço"]].copy()
                df_tab["Preço"] = df_tab["Preço"].apply(formatar_moeda)
                st.table(df_tab)
    else:
        st.warning("Nenhum dado encontrado.")

# --- ABA 3: CONFIGURAÇÕES E EDIÇÃO (MODIFICADA) ---
with tab_config:
    st.title("⚙️ Ajustes e Gerenciamento")
    
    st.subheader("🛠️ Editar ou Excluir Itens")
    num_comanda = st.number_input("Número da comanda:", min_value=1, step=1)
    
    df_db = get_data()
    if not df_db.empty:
        # Filtra os itens da comanda selecionada
        itens_comanda = df_db[df_db['Comanda'] == num_comanda]
        
        if not itens_comanda.empty:
            st.info(f"Editando Comanda #{num_comanda} de: {itens_comanda['Nome'].iloc[0]}")
            
            for idx, row in itens_comanda.iterrows():
                with st.container():
                    col_item, col_preco, col_btn = st.columns([3, 1.5, 1])
                    
                    # Campos de edição com valores atuais como padrão
                    novo_nome_item = col_item.text_input("Item:", value=row['Item'], key=f"edit_item_{idx}")
                    novo_preco = col_preco.number_input("Preço (R$):", value=float(row['Preço']), step=0.5, key=f"edit_preco_{idx}")
                    
                    c_del, c_save = col_btn.columns(2)
                    
                    # Botão para Excluir o item específico
                    if c_del.button("🗑️", key=f"del_db_{idx}", help="Excluir este item"):
                        df_base = conn.read(worksheet="Sheet1", ttl=0)
                        df_nova = df_base.drop(idx)
                        conn.update(worksheet="Sheet1", data=df_nova)
                        st.cache_data.clear()
                        st.success("Item removido!")
                        time.sleep(1)
                        st.rerun()

                    # Botão para Salvar Alterações do item específico
                    if c_save.button("💾", key=f"save_db_{idx}", help="Salvar alterações"):
                        df_base = conn.read(worksheet="Sheet1", ttl=0)
                        # Atualiza os valores no DataFrame original usando o índice
                        df_base.at[idx, 'Item'] = novo_nome_item
                        df_base.at[idx, 'Preço'] = novo_preco
                        
                        conn.update(worksheet="Sheet1", data=df_base)
                        st.cache_data.clear()
                        st.success("Alteração salva!")
                        time.sleep(1)
                        st.rerun()
                st.divider()
        else:
            st.write("Nenhum registro encontrado para esta comanda.")
