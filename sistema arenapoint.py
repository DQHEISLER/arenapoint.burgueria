import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Sistema Oficial", layout="wide", page_icon="🍔")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CARDÁPIO CENTRALIZADO (Para usar na Venda e na Edição) ---
CARDAPIO = {
    "HAMBÚRGUER": {"🍔 Simples": 15.0, "🍔 Duplo": 20.0, "🍔 Triplo": 26.0},
    "ESPETOS": {"🍢 Carne": 8.0, "🍢 Frango": 8.0},
    "BEBIDAS": {"🥤 Água": 4.0, "🥤 Lata": 5.0, "🥤 1 Litro": 8.0, "🥤 2 Litros": 18.0},
    "OFERTA/SINUCA": {"🎱 Sinuca/Valor Manual": 0.0}
}

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
        cat = st.radio("Categoria", list(CARDAPIO.keys()), key="cat_venda")
        if cat == "OFERTA/SINUCA":
            item_nome = "🎱 Oferta/Sinuca"
            preco = st.number_input("Valor (R$):", min_value=0.0, step=1.0, key="preco_manual_venda")
        else:
            item_nome = st.selectbox("Produto", list(CARDAPIO[cat].keys()), key="prod_venda")
            preco = CARDAPIO[cat][item_nome]
        obs = st.text_input("📝 Personalizar (Opcional):", placeholder="Ex: Sem cebola", key="obs_venda")
        
        if st.button("➕ Adicionar Item", use_container_width=True):
            cliente_final = st.session_state.nome_cliente if st.session_state.nome_cliente else "Cliente Avulso"
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda, 
                "Nome": cliente_final, 
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                "Item": f"{item_nome} ({obs})" if obs else item_nome, 
                "Preço": float(preco)
            })
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
                if c_b.button("🗑️", key=f"del_cart_{i}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()
            st.divider()
            st.write(f"### Total: {formatar_moeda(df_cart['Preço'].sum())}")
            if st.button("✅ FINALIZAR E SALVAR", type="primary", use_container_width=True):
                df_online = conn.read(worksheet="Sheet1", ttl=0)
                df_final = pd.concat([df_online, df_cart], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df_final)
                st.session_state.carrinho, st.session_state.nome_cliente = [], ""
                st.cache_data.clear()
                st.success("Pedido Salvo!")
                time.sleep(1)
                st.rerun()
        else:
            st.info("O carrinho está vazio.")

# --- ABA 2: RELATÓRIOS ---
with tab_relatorios:
    st.title("📊 Relatórios Financeiros")
    df_vendas = get_data()
    if not df_vendas.empty:
        hoje = datetime.now().strftime('%Y-%m-%d')
        df_hoje = df_vendas[df_vendas['Data_Texto'] == hoje]
        df_mes = df_vendas[df_vendas['Data_DT'].dt.month == datetime.now().month]
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Hoje", formatar_moeda(df_hoje['Preço'].sum()))
        c2.metric("🗓️ Mês", formatar_moeda(df_mes['Preço'].sum()))
        c3.metric("📦 Pedidos", len(df_hoje['Comanda'].unique()))
        st.divider()
        ids = sorted(df_vendas['Comanda'].unique(), reverse=True)
        for id_c in ids:
            dados = df_vendas[df_vendas['Comanda'] == id_c]
            with st.expander(f"Comanda #{int(id_c)} - {dados['Nome'].iloc[0]} | Total: {formatar_moeda(dados['Preço'].sum())}"):
                st.table(dados[["Item", "Preço"]].assign(Preço=lambda x: x['Preço'].apply(formatar_moeda)))
    else:
        st.warning("Nenhum dado.")

# --- ABA 3: CONFIGURAÇÕES E EDIÇÃO ---
with tab_config:
    st.title("⚙️ Ajustes e Gerenciamento")
    num_comanda = st.number_input("Número da comanda para editar/adicionar:", min_value=1, step=1)
    df_db = get_data()
    
    if not df_db.empty:
        itens_comanda = df_db[df_db['Comanda'] == num_comanda]
        
        if not itens_comanda.empty:
            st.info(f"Gerenciando Comanda #{num_comanda} - Cliente: {itens_comanda['Nome'].iloc[0]}")
            
            # --- SEÇÃO: ADICIONAR NOVO ITEM ---
            with st.expander("➕ Adicionar Novo Item nesta Comanda", expanded=False):
                c_add1, c_add2 = st.columns(2)
                with c_add1:
                    cat_new = st.selectbox("Categoria", list(CARDAPIO.keys()), key="cat_add")
                    if cat_new == "OFERTA/SINUCA":
                        item_new_name = "🎱 Oferta/Sinuca"
                        preco_new = st.number_input("Valor (R$):", min_value=0.0, key="val_add")
                    else:
                        item_new_name = st.selectbox("Produto", list(CARDAPIO[cat_new].keys()), key="prod_add")
                        preco_new = CARDAPIO[cat_new][item_new_name]
                with c_add2:
                    obs_new = st.text_input("Observação:", key="obs_add")
                    if st.button("Gravar Novo Item", type="primary", use_container_width=True):
                        df_original = conn.read(worksheet="Sheet1", ttl=0)
                        novo_row = {
                            "Comanda": num_comanda,
                            "Nome": itens_comanda['Nome'].iloc[0],
                            "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Item": f"{item_new_name} ({obs_new})" if obs_new else item_new_name,
                            "Preço": float(preco_new)
                        }
                        df_atualizado = pd.concat([df_original, pd.DataFrame([novo_row])], ignore_index=True)
                        conn.update(worksheet="Sheet1", data=df_atualizado)
                        st.cache_data.clear()
                        st.success("Item Adicionado!")
                        time.sleep(1)
                        st.rerun()

            st.divider()
            st.subheader("📝 Itens Atuais (Editar/Excluir)")
            
            # --- SEÇÃO: EDITAR ITENS EXISTENTES ---
            for idx, row in itens_comanda.iterrows():
                with st.expander(f"Editar: {row['Item']} - {formatar_moeda(row['Preço'])}"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        # Estilo igual ao da Venda
                        cat_edit = st.selectbox("Nova Categoria", list(CARDAPIO.keys()), key=f"cat_ed_{idx}")
                        if cat_edit == "OFERTA/SINUCA":
                            item_ed_name = "🎱 Oferta/Sinuca"
                            preco_ed = st.number_input("Novo Valor (R$):", value=float(row['Preço']), key=f"val_ed_{idx}")
                        else:
                            item_ed_name = st.selectbox("Novo Produto", list(CARDAPIO[cat_edit].keys()), key=f"prod_ed_{idx}")
                            preco_ed = CARDAPIO[cat_edit][item_ed_name]
                    with col_e2:
                        obs_ed = st.text_input("Nova Observação:", key=f"obs_ed_{idx}")
                        
                        btn_col1, btn_col2 = st.columns(2)
                        if btn_col1.button("💾 Salvar Alteração", key=f"save_{idx}", use_container_width=True):
                            df_base = conn.read(worksheet="Sheet1", ttl=0)
                            df_base.at[idx, 'Item'] = f"{item_ed_name} ({obs_ed})" if obs_ed else item_ed_name
                            df_base.at[idx, 'Preço'] = float(preco_ed)
                            conn.update(worksheet="Sheet1", data=df_base)
                            st.cache_data.clear()
                            st.success("Item Atualizado!")
                            time.sleep(1)
                            st.rerun()
                        
                        if btn_col2.button("🗑️ Excluir Item", key=f"del_{idx}", use_container_width=True):
                            df_base = conn.read(worksheet="Sheet1", ttl=0)
                            df_base = df_base.drop(idx)
                            conn.update(worksheet="Sheet1", data=df_base)
                            st.cache_data.clear()
                            st.rerun()
        else:
            st.write("Comanda não encontrada.")
