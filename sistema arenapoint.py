import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Sistema Oficial", layout="wide", page_icon="🍔")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURAÇÃO DO CARDÁPIO ---
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
            return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço", "Status", "Pagamento"])
        
        # Garantir colunas novas
        for col in ["Status", "Pagamento"]:
            if col not in df.columns:
                df[col] = "Pendente"
        
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
        return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço", "Status", "Pagamento"])

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'carrinho' not in st.session_state: st.session_state.carrinho = []
if 'nome_cliente' not in st.session_state: st.session_state.nome_cliente = ""

# --- INTERFACE POR ABAS ---
tab_vendas, tab_relatorios, tab_config = st.tabs(["🛒 Nova Venda", "📊 Relatórios/Cozinha", "⚙️ Ajustes"])

# --- ABA 1: VENDAS ---
with tab_vendas:
    df_vendas_atual = get_data()
    proxima_comanda = int(df_vendas_atual['Comanda'].max() if not df_vendas_atual.empty else 0) + 1
    st.title("🍔 Arena Point - Caixa")
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.subheader("📝 Dados do Pedido")
        st.session_state.nome_cliente = st.text_input("Nome do Cliente:", value=st.session_state.nome_cliente, placeholder="Ex: Diego")
        
        cat = st.radio("Categoria", list(cardapio_base.keys()), key="cat_venda")
        item_final_nome, preco_final = "", 0.0

        if cat == "HAMBÚRGUER":
            hamb = st.selectbox("Escolha o Hambúrguer", list(cardapio_base[cat].keys()))
            escolha_adicional = st.multiselect("Adicionais:", list(adicionais_opcoes.keys()))
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

        obs = st.text_input("📝 Personalizar:", placeholder="Ex: Sem cebola", key="obs_venda")
        if st.button("➕ Adicionar ao Pedido", use_container_width=True):
            cliente_final = st.session_state.nome_cliente if st.session_state.nome_cliente else "Cliente Avulso"
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda, "Nome": cliente_final, 
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                "Item": f"{item_final_nome} | Obs: {obs}" if obs else item_final_nome, 
                "Preço": float(preco_final),
                "Status": "Pendente",
                "Pagamento": "Aguardando"
            })
            st.rerun()

    with col2:
        st.subheader(f"📋 Itens da Comanda #{proxima_comanda}")
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            total_pedido = df_cart['Preço'].sum()
            
            for i, row in df_cart.iterrows():
                st.write(f"**{row['Item']}** - {formatar_moeda(row['Preço'])}")
            
            st.divider()
            st.write(f"### Total: {formatar_moeda(total_pedido)}")
            
            forma_pag = st.selectbox("💳 Forma de Pagamento:", ["Dinheiro", "Pix", "Cartão Débito", "Cartão Crédito"])
            
            if st.button("✅ FINALIZAR E SALVAR", type="primary", use_container_width=True):
                df_cart['Pagamento'] = forma_pag # Atribui a forma escolhida
                df_online = conn.read(worksheet="Sheet1", ttl=0)
                conn.update(worksheet="Sheet1", data=pd.concat([df_online, df_cart], ignore_index=True))
                st.session_state.carrinho, st.session_state.nome_cliente = [], ""
                st.cache_data.clear(); st.success("Pedido Gravado!"); time.sleep(1); st.rerun()
            
            if st.button("🗑️ Esvaziar Carrinho"):
                st.session_state.carrinho = []; st.rerun()
        else: st.info("Carrinho vazio.")

# --- ABA 2: RELATÓRIOS E COZINHA (COM CORES) ---
with tab_relatorios:
    st.title("📊 Gestão de Pedidos e Cores")
    df_vendas = get_data()
    
    if not df_vendas.empty:
        # Filtros de visualização
        ids = sorted(df_vendas['Comanda'].unique(), reverse=True)
        
        for id_c in ids:
            dados = df_vendas[df_vendas['Comanda'] == id_c]
            status_atual = dados['Status'].iloc[0]
            pag_atual = dados['Pagamento'].iloc[0]
            nome_c = dados['Nome'].iloc[0]
            total_c = dados['Preço'].sum()

            # Lógica de Cores visuais
            container_color = "white"
            emoji_status = "🔵"
            
            if status_atual == "Prioridade": 
                st.error(f"🚨 PRIORIDADE - Comanda #{id_c} - {nome_c}")
            elif status_atual == "Pronto":
                st.warning(f"🔔 PRONTO/AGUARDANDO - Comanda #{id_c} - {nome_c}")
            elif status_atual == "Pago":
                st.success(f"✅ PAGO - Comanda #{id_c} - {nome_c} ({pag_atual})")
            else:
                st.info(f"⏳ EM PREPARO - Comanda #{id_c} - {nome_c}")

            with st.expander(f"Detalhes da Comanda #{id_c}"):
                st.table(dados[["Item", "Preço", "Pagamento"]])
                
                # Botões de mudança de cor/status
                c1, c2, c3, c4 = st.columns(4)
                if c1.button("🔴 Prioridade", key=f"pri_{id_c}"):
                    df_full = conn.read(worksheet="Sheet1", ttl=0)
                    df_full.loc[df_full['Comanda'] == id_c, 'Status'] = "Prioridade"
                    conn.update(worksheet="Sheet1", data=df_full); st.cache_data.clear(); st.rerun()
                
                if c2.button("🟡 Pronto", key=f"pro_{id_c}"):
                    df_full = conn.read(worksheet="Sheet1", ttl=0)
                    df_full.loc[df_full['Comanda'] == id_c, 'Status'] = "Pronto"
                    conn.update(worksheet="Sheet1", data=df_full); st.cache_data.clear(); st.rerun()
                
                if c3.button("🟢 Marcar Pago", key=f"pag_{id_c}"):
                    df_full = conn.read(worksheet="Sheet1", ttl=0)
                    df_full.loc[df_full['Comanda'] == id_c, 'Status'] = "Pago"
                    conn.update(worksheet="Sheet1", data=df_full); st.cache_data.clear(); st.rerun()
                
                if c4.button("🔵 Normal", key=f"norm_{id_c}"):
                    df_full = conn.read(worksheet="Sheet1", ttl=0)
                    df_full.loc[df_full['Comanda'] == id_c, 'Status'] = "Pendente"
                    conn.update(worksheet="Sheet1", data=df_full); st.cache_data.clear(); st.rerun()

# --- ABA 3: AJUSTES ---
with tab_config:
    st.title("⚙️ Ajustes de Planilha")
    num_comanda = st.number_input("Buscar Comanda:", min_value=1, step=1)
    df_db = get_data()
    
    if not df_db.empty:
        itens_comanda = df_db[df_db['Comanda'] == num_comanda]
        if not itens_comanda.empty:
            for idx, row in itens_comanda.iterrows():
                col_i, col_p, col_pay, col_btn = st.columns([3, 1, 1, 1])
                novo_item = col_i.text_input("Item", row['Item'], key=f"edit_i_{idx}")
                novo_preco = col_p.number_input("Preço", float(row['Preço']), key=f"edit_p_{idx}")
                novo_pag = col_pay.selectbox("Pag", ["Dinheiro", "Pix", "Cartão Débito", "Cartão Crédito"], index=0, key=f"edit_pay_{idx}")
                
                if col_btn.button("💾", key=f"save_{idx}"):
                    df_orig = conn.read(worksheet="Sheet1", ttl=0)
                    df_orig.at[idx, 'Item'] = novo_item
                    df_orig.at[idx, 'Preço'] = novo_preco
                    df_orig.at[idx, 'Pagamento'] = novo_pag
                    conn.update(worksheet="Sheet1", data=df_orig)
                    st.cache_data.clear(); st.success("Atualizado!"); time.sleep(0.5); st.rerun()
