import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Sistema Oficial", layout="wide", page_icon="🍔")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURAÇÃO DO CARDÁPIO (CENTRALIZADO) ---
cardapio_base = {
    "HAMBÚRGUER": {"🍔 Simples": 15.0, "🍔 Duplo": 20.0, "🍔 Triplo": 26.0},
    "ESPETOS": {"🍢 Simples": 12.0, "🍢 Completo": 20.0, "🍢 Apenas Espeto": 8.0},
    "BATATA FRITA": {
        "🍟 Simples Pequena (250g)": 15.0, "🍟 Simples Média (500g)": 30.0, "🍟 Simples Grande (1kg)": 45.0,
        "🍟 Cheddar e Bacon P (250g)": 25.0, "🍟 Cheddar e Bacon M (500g)": 42.0, "🍟 Cheddar e Bacon G (1kg)": 60.0
    },
    "BEBIDAS": {
        "🥤 Água com Gás": 4.0, "🥤 Refrigerante KS": 5.0, "🥤 Refrigerante Lata": 5.0, 
        "🥤 Refrigerante 1 Litro": 8.0, "🥤 Refrigerante 2 Litros": 18.0
    },
    "OUTROS": {"🎱 Sinuca/Valor Manual": 0.0}
}
adicionais_opcoes = {"➕ Mussarela": 2.0, "➕ Bacon": 6.0, "➕ Carne Extra": 5.0}

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
        st.subheader("🍔 Menu Inteligente")
        
        cat = st.radio("Categoria", list(cardapio_base.keys()), key="cat_venda")
        item_final_nome, preco_final = "", 0.0

        if cat == "HAMBÚRGUER":
            hamb = st.selectbox("Escolha o Hambúrguer", list(cardapio_base[cat].keys()))
            escolha_adicional = st.multiselect("Adicionais para este Hambúrguer:", list(adicionais_opcoes.keys()))
            preco_final = cardapio_base[cat][hamb] + sum([adicionais_opcoes[x] for x in escolha_adicional])
            item_final_nome = f"{hamb}{' + ' + ', '.join(escolha_adicional) if escolha_adicional else ''}"
        elif cat == "ESPETOS":
            espeto_tipo = st.selectbox("Escolha o Prato", list(cardapio_base[cat].keys()))
            proteina = st.radio("Sabor do Espeto:", ["Carne", "Frango"], horizontal=True)
            preco_final = cardapio_base[cat][espeto_tipo]
            item_final_nome = f"{espeto_tipo} ({proteina})"
        elif cat == "OUTROS":
            item_final_nome = "🎱 Sinuca/Valor Manual"
            preco_final = st.number_input("Valor (R$):", min_value=0.0, step=1.0, key="val_manual_venda")
        else:
            item_final_nome = st.selectbox("Produto", list(cardapio_base[cat].keys()))
            preco_final = cardapio_base[cat][item_final_nome]

        obs = st.text_input("📝 Personalizar (Opcional):", placeholder="Ex: Sem cebola", key="obs_venda")
        if st.button("➕ Adicionar ao Pedido", use_container_width=True):
            cliente_final = st.session_state.nome_cliente if st.session_state.nome_cliente else "Cliente Avulso"
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda, "Nome": cliente_final, 
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                "Item": f"{item_final_nome} | Obs: {obs}" if obs else item_final_nome, 
                "Preço": float(preco_final)
            })
            st.toast(f"Adicionado: {item_final_nome}")
            st.rerun()

    with col2:
        st.subheader(f"📋 Comanda #{proxima_comanda}")
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            for i, row in df_cart.iterrows():
                c_i, c_p, c_b = st.columns([3, 1, 1])
                c_i.write(row['Item']); c_p.write(formatar_moeda(row['Preço']))
                if c_b.button("🗑️", key=f"del_{i}"):
                    st.session_state.carrinho.pop(i); st.rerun()
            st.divider()
            if st.button("✅ FINALIZAR E SALVAR", type="primary", use_container_width=True):
                df_online = conn.read(worksheet="Sheet1", ttl=0)
                conn.update(worksheet="Sheet1", data=pd.concat([df_online, df_cart], ignore_index=True))
                st.session_state.carrinho, st.session_state.nome_cliente = [], ""
                st.cache_data.clear(); st.success("Pedido Gravado!"); time.sleep(1); st.rerun()
        else: st.info("O carrinho está vazio.")

# --- ABA 2: RELATÓRIOS ---
with tab_relatorios:
    st.title("📊 Relatórios Financeiros")
    if st.button("🔄 Sincronizar Dados"): st.cache_data.clear(); st.rerun()
    df_vendas = get_data()
    if not df_vendas.empty:
        hoje_ref = datetime.now().strftime('%Y-%m-%d')
        df_hoje = df_vendas[df_vendas['Data_Texto'] == hoje_ref]
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Hoje", formatar_moeda(df_hoje['Preço'].sum()))
        c2.metric("🗓️ Mensal", formatar_moeda(df_vendas[df_vendas['Data_DT'].dt.month == datetime.now().month]['Preço'].sum()))
        c3.metric("📦 Pedidos", len(df_hoje['Comanda'].unique()))
        st.divider()
        ids = sorted(df_vendas['Comanda'].unique(), reverse=True)
        for id_c in ids:
            dados = df_vendas[df_vendas['Comanda'] == id_c]
            with st.expander(f"Comanda #{int(id_c)} - {dados['Nome'].iloc[0]} | Total: {formatar_moeda(dados['Preço'].sum())}"):
                st.table(dados[["Item", "Preço"]])

# --- ABA 3: AJUSTES E ADIÇÃO EM COMANDA EXISTENTE ---
with tab_config:
    st.title("⚙️ Gerenciamento de Comandas Lançadas")
    num_comanda = st.number_input("Buscar Comanda para Editar/Adicionar:", min_value=1, step=1)
    df_db = get_data()
    
    if not df_db.empty:
        itens_comanda = df_db[df_db['Comanda'] == num_comanda]
        if not itens_comanda.empty:
            nome_cliente_atual = itens_comanda['Nome'].iloc[0]
            
            # PARTE NOVA: ADICIONAR ITEM NA COMANDA JÁ LANÇADA
            with st.expander("➕ ADICIONAR NOVO ITEM NESTA COMANDA", expanded=False):
                col_add1, col_add2 = st.columns(2)
                with col_add1:
                    cat_add = st.radio("Categoria", list(cardapio_base.keys()), key="cat_add")
                with col_add2:
                    if cat_add == "HAMBÚRGUER":
                        h_add = st.selectbox("Hambúrguer", list(cardapio_base[cat_add].keys()), key="h_add")
                        a_add = st.multiselect("Adicionais", list(adicionais_opcoes.keys()), key="a_add")
                        p_final_add = cardapio_base[cat_add][h_add] + sum([adicionais_opcoes[x] for x in a_add])
                        n_final_add = f"{h_add}{' + ' + ', '.join(a_add) if a_add else ''}"
                    elif cat_add == "ESPETOS":
                        e_add = st.selectbox("Prato", list(cardapio_base[cat_add].keys()), key="e_add")
                        s_add = st.radio("Sabor:", ["Carne", "Frango"], horizontal=True, key="s_add")
                        p_final_add = cardapio_base[cat_add][e_add]
                        n_final_add = f"{e_add} ({s_add})"
                    elif cat_add == "OUTROS":
                        n_final_add = "🎱 Sinuca/Valor Manual"
                        p_final_add = st.number_input("Valor (R$):", min_value=0.0, step=1.0, key="val_manual_add")
                    else:
                        n_final_add = st.selectbox("Produto", list(cardapio_base[cat_add].keys()), key="p_add")
                        p_final_add = cardapio_base[cat_add][n_final_add]
                    
                    obs_add = st.text_input("Observações:", key="obs_add")
                    if st.button("💾 INSERIR NA COMANDA", type="primary", use_container_width=True):
                        novo_reg = pd.DataFrame([{
                            "Comanda": num_comanda, "Nome": nome_cliente_atual,
                            "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Item": f"{n_final_add} | Obs: {obs_add}" if obs_add else n_final_add,
                            "Preço": float(p_final_add)
                        }])
                        df_full = conn.read(worksheet="Sheet1", ttl=0)
                        conn.update(worksheet="Sheet1", data=pd.concat([df_full, novo_reg], ignore_index=True))
                        st.cache_data.clear(); st.success("Item Adicionado!"); time.sleep(1); st.rerun()

            st.divider()
            st.subheader(f"📝 Itens Atuais da Comanda #{num_comanda}")
            for idx, row in itens_comanda.iterrows():
                with st.container():
                    c_n, c_i, c_p, c_b = st.columns([1.5, 2.5, 1, 1])
                    n_n = c_n.text_input("Cliente", value=row['Nome'], key=f"n_{idx}")
                    n_i = c_i.text_input("Item", value=row['Item'], key=f"i_{idx}")
                    n_p = c_p.number_input("R$", value=float(row['Preço']), key=f"p_{idx}")
                    
                    btn_save, btn_del = c_b.columns(2)
                    if btn_save.button("💾", key=f"s_{idx}"):
                        df_orig = conn.read(worksheet="Sheet1", ttl=0)
                        df_orig.at[idx, ['Nome', 'Item', 'Preço']] = [n_n, n_i, n_p]
                        conn.update(worksheet="Sheet1", data=df_orig)
                        st.cache_data.clear(); st.success("Salvo!"); time.sleep(0.5); st.rerun()
                    if btn_del.button("🗑️", key=f"d_{idx}"):
                        df_orig = conn.read(worksheet="Sheet1", ttl=0)
                        conn.update(worksheet="Sheet1", data=df_orig.drop(idx))
                        st.cache_data.clear(); st.error("Removido!"); time.sleep(0.5); st.rerun()
        else: st.info("Comanda não encontrada.")
