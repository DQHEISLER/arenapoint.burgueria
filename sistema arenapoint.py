import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- INTERFACE POR ABAS ---
tab_vendas, tab_relatorios, tab_config = st.tabs(["🛒 Nova Venda", "📊 Relatórios", "⚙️ Ajustes e Config"])

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Sistema Oficial", layout="wide", page_icon="🍔")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE UTILIDADE ---
def formatar_moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
    except:
        return "R$ 0,00"

@st.cache_data(ttl=2) 
def get_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])
        
        if 'Preço' in df.columns:
            def limpar_valor(v):
                if isinstance(v, (int, float)): return float(v)
                v = str(v).replace('R$', '').strip()
                if not v or v.lower() == 'nan': return 0.0
                if '.' in v and ',' in v: v = v.replace('.', '')
                v = v.replace(',', '.')
                try: return float(v)
                except: return 0.0
            df['Preço'] = df['Preço'].apply(limpar_valor)
        
        df['Comanda'] = pd.to_numeric(df['Comanda'], errors='coerce').fillna(0).astype(int)
        df['Data_DT'] = pd.to_datetime(df['Data'], errors='coerce')
        df['Data_Texto'] = df['Data_DT'].dt.strftime('%Y-%m-%d')
        return df
    except Exception as e:
        st.error(f"❌ ERRO DE LEITURA: {e}")
        return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'carrinho' not in st.session_state: st.session_state.carrinho = []
if 'nome_cliente' not in st.session_state: st.session_state.nome_cliente = ""

# --- INTERFACE POR ABAS ---
tab_vendas, tab_relatorios, tab_config = st.tabs(["🛒 Nova Venda", "📊 Relatórios", "⚙️ Ajustes e Config"])

# --- ABA 1: VENDAS ---
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
        
        # Definição do cardápio com sub-produtos
        cardapio_base = {
            "HAMBÚRGUER": {"🍔 Simples": 15.0, "🍔 Duplo": 20.0, "🍔 Triplo": 26.0},
            "ESPETOS": {"🍢 Simples": 12.0, "🍢 Completo": 20.0, "🍢 Apenas Espeto": 8.0},
            "BATATA FRITA": {
                "🍟 Simples Pequena": 15.0, "🍟 Simples Média": 30.0, "🍟 Simples Grande": 45.0,
                "🍟 Cheddar e Bacon P": 25.0, "🍟 Cheddar e Bacon M": 42.0, "🍟 Cheddar e Bacon G": 60.0
            },
            "BEBIDAS": {"🥤 Água": 4.0, "🥤 Refri KS": 5.0, "🥤 Refri Lata": 5.0, "🥤 Refri 1L": 8.0, "🥤 Refri 2L": 18.0},
            "OUTROS": {"🎱 Sinuca/Manual": 0.0}
        }
        
        adicionais_hamburguer = {"➕ Mussarela": 2.0, "➕ Bacon": 6.0, "➕ Carne Extra": 5.0}

        cat = st.radio("Categoria", list(cardapio_base.keys()))
        
        item_final = ""
        preco_final = 0.0

        if cat == "HAMBÚRGUER":
            escolha = st.selectbox("Selecione o Hambúrguer", list(cardapio_base[cat].keys()))
            adicionais = st.multiselect("Adicionais", list(adicionais_hamburguer.keys()))
            preco_final = cardapio_base[cat][escolha] + sum([adicionais_hamburguer[a] for a in adicionais])
            item_final = f"{escolha} {'+ ' + ', '.join(adicionais) if adicionais else ''}"
        
        elif cat == "ESPETOS":
            escolha = st.selectbox("Selecione o Prato", list(cardapio_base[cat].keys()))
            sabor = st.radio("Sabor:", ["Carne", "Frango"], horizontal=True)
            preco_final = cardapio_base[cat][escolha]
            item_final = f"{escolha} ({sabor})"
        
        elif cat == "OUTROS":
            item_final = "🎱 Sinuca/Valor Manual"
            preco_final = st.number_input("Valor (R$):", min_value=0.0, step=1.0)
        else:
            escolha = st.selectbox("Produto", list(cardapio_base[cat].keys()))
            item_final = escolha
            preco_final = cardapio_base[cat][escolha]
            
        obs = st.text_input("📝 Observações (Opcional):")
        
        if st.button("➕ Adicionar Item", use_container_width=True):
            cliente_final = st.session_state.nome_cliente if st.session_state.nome_cliente else "Cliente Avulso"
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda, 
                "Nome": cliente_final, 
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                "Item": f"{item_final} | Obs: {obs}" if obs else item_final, 
                "Preço": float(preco_final)
            })
            st.toast(f"Adicionado: {item_final}")
            st.rerun()

    with col2:
        # ... (Mantido o código de exibição do carrinho igual ao seu original)
        st.subheader(f"📋 Comanda #{proxima_comanda}")
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            for i, row in df_cart.iterrows():
                c_i, c_p, c_b = st.columns([3, 1, 1])
                c_i.write(row['Item'])
                c_p.write(formatar_moeda(row['Preço']))
                if c_b.button("🗑️", key=f"del_{i}"):
                    st.session_state.carrinho.pop(i); st.rerun()
            st.divider()
            st.write(f"### Total: {formatar_moeda(df_cart['Preço'].sum())}")
            if st.button("✅ FINALIZAR E SALVAR", type="primary", use_container_width=True):
                df_online = conn.read(worksheet="Sheet1", ttl=0)
                conn.update(worksheet="Sheet1", data=pd.concat([df_online, df_cart], ignore_index=True))
                st.session_state.carrinho, st.session_state.nome_cliente = [], ""
                st.cache_data.clear(); st.success("Pedido Salvo!"); time.sleep(1); st.rerun()

# --- ABA 2: RELATÓRIOS ---
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
        c1.metric("💰 Hoje", formatar_moeda(df_hoje['Preço'].sum()))
        c2.metric("🗓️ Mensal", formatar_moeda(df_mes['Preço'].sum()))
        c3.metric("📦 Pedidos", len(df_hoje['Comanda'].unique()))
        
        st.divider()
        st.subheader("📂 Histórico")
        ids = sorted(df_vendas['Comanda'].unique(), reverse=True)
        for id_c in ids:
            dados = df_vendas[df_vendas['Comanda'] == id_c]
            total_c = dados['Preço'].sum()
            with st.expander(f"Comanda #{int(id_c)} - {dados['Nome'].iloc[0]} | Total: {formatar_moeda(total_c)}"):
                df_tab = dados[["Item", "Preço"]].copy()
                df_tab["Preço"] = df_tab["Preço"].apply(formatar_moeda)
                st.table(df_tab)

# --- ABA 3: CONFIGURAÇÕES ---
with tab_config:
    st.title("⚙️ Ajustes")
    num_comanda = st.number_input("Buscar Comanda:", min_value=1, step=1)
    df_db = get_data()
    if not df_db.empty:
        itens_comanda = df_db[df_db['Comanda'] == num_comanda]
        if not itens_comanda.empty:
            for idx, row in itens_comanda.iterrows():
                with st.container():
                    col_item, col_preco, col_btn = st.columns([3, 1.5, 1])
                    novo_item = col_item.text_input("Item:", value=row['Item'], key=f"ed_it_{idx}")
                    novo_p = col_preco.number_input("R$:", value=float(row['Preço']), key=f"ed_pr_{idx}")
                    if col_btn.button("💾", key=f"sv_{idx}"):
                        df_base = conn.read(worksheet="Sheet1", ttl=0)
                        df_base.at[idx, 'Item'] = novo_item
                        df_base.at[idx, 'Preço'] = novo_p
                        conn.update(worksheet="Sheet1", data=df_base)
                        st.cache_data.clear()
                        st.success("Salvo!")
                        st.rerun()
