import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Gestão Total", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO PARA LER DADOS SEM CACHE ---
def get_data():
    try:
        return conn.read(worksheet="Sheet1", ttl=0) 
    except:
        return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []
if 'nome_cliente' not in st.session_state:
    st.session_state.nome_cliente = ""

df_vendas_atual = get_data()

# Lógica para número da comanda
if not df_vendas_atual.empty:
    df_vendas_atual['Comanda'] = pd.to_numeric(df_vendas_atual['Comanda'], errors='coerce')
    proxima_comanda = int(df_vendas_atual['Comanda'].max()) + 1
else:
    proxima_comanda = 1

# --- CARDÁPIO ---
cardapio = {
    "HAMBÚRGUER": {"🍔 Simples": 15.0, "🍔 Duplo": 20.0, "🍔 Triplo": 26.0},
    "ESPETOS": {"🍢 Carne": 8.0, "🍢 Frango": 8.0},
    "BEBIDAS": {"🥤 Água": 4.0, "🥤 Lata": 5.0, "🥤 1 Litro": 8.0, "🥤 2 Litros": 18.0},
    "OFERTA/SINUCA": {"🎱 Sinuca/Valor Manual": 0.0}
}

# --- INTERFACE POR ABAS ---
tab_vendas, tab_relatorios, tab_config = st.tabs(["🛒 Nova Venda", "📊 Relatórios", "⚙️ Ajustes e Config"])

with tab_vendas:
    st.title("🍔 Arena Point - Caixa")
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("📝 Dados do Pedido")
        nome_input = st.text_input("Nome do Cliente:", value=st.session_state.nome_cliente, placeholder="Ex: Diego")
        st.session_state.nome_cliente = nome_input

        st.divider()
        st.subheader("🍔 Menu")
        cat = st.radio("Categoria", list(cardapio.keys()))
        
        if cat == "OFERTA/SINUCA":
            item_nome = "🎱 Oferta/Sinuca"
            valor_manual = st.number_input("Digite o valor (R$):", min_value=0.0, step=1.0)
            preco = valor_manual
        else:
            item_nome = st.selectbox("Produto", list(cardapio[cat].keys()))
            preco = cardapio[cat][item_nome]
        
        if st.button("➕ Adicionar Item", use_container_width=True):
            cliente_final = st.session_state.nome_cliente if st.session_state.nome_cliente else "Cliente Avulso"
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda,
                "Nome": cliente_final,
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Item": item_nome,
                "Preço": preco
            })
            st.toast(f"{item_nome} adicionado!")
            st.rerun()

    with col2:
        st.subheader(f"📋 Itens da Comanda #{proxima_comanda}")
        
        if st.session_state.carrinho:
            for i, item in enumerate(st.session_state.carrinho):
                c_item, c_preco, c_btn = st.columns([3, 1, 1])
                c_item.write(f"**{item['Item']}**")
                c_preco.write(f"R$ {item['Preço']:.2f}")
                if c_btn.button("🗑️", key=f"btn_carrinho_{i}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()
            
            st.divider()
            df_cart = pd.DataFrame(st.session_state.carrinho)
            total_comanda = df_cart["Preço"].sum()
            st.write(f"### Total: R$ {total_comanda:.2f}")

            if st.button("✅ Finalizar e Salvar Pedido", type="primary", use_container_width=True):
                df_antigo = get_data()
                df_final = pd.concat([df_antigo, df_cart], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df_final)
                st.success(f"Pedido #{proxima_comanda} salvo!")
                st.session_state.carrinho = []
                st.session_state.nome_cliente = ""
                st.rerun()
        else:
            st.info("O carrinho está vazio.")

with tab_relatorios:
    st.title("📊 Controle de Faturamento")
    df_vendas = get_data()
    if not df_vendas.empty:
        df_vendas['Data'] = pd.to_datetime(df_vendas['Data'])
        hoje = datetime.now().date()
        fatur_dia = df_vendas[df_vendas['Data'].dt.date == hoje]['Preço'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Faturamento Hoje", f"R$ {fatur_dia:.2f}")
        c2.metric("Total de Pedidos", len(df_vendas['Comanda'].unique()))

        st.divider()
        st.subheader("📂 Histórico de Comandas")
        ids_reversos = sorted(df_vendas['Comanda'].unique(), reverse=True)
        for id_c in ids_reversos:
            detalhe = df_vendas[df_vendas['Comanda'] == id_c]
            nome_c = detalhe['Nome'].iloc[0] if 'Nome' in detalhe.columns else "N/A"
            with st.expander(f"📦 Comanda #{int(id_c)} - {nome_c}"):
                st.table(detalhe[["Item", "Preço"]])
                st.write(f"**Total: R$ {detalhe['Preço'].sum():.2f}**")

with tab_config:
    st.title("⚙️ Ajustes de Sistema")
    
    # --- MUDAR NÚMERO DA COMANDA ---
    st.subheader("🔄 Mudar Número de Comanda")
    col_alt1, col_alt2 = st.columns(2)
    with col_alt1:
        comanda_errada = st.number_input("De Comanda:", min_value=1, step=1)
    with col_alt2:
        comanda_certa = st.number_input("Para Comanda:", min_value=1, step=1)
    
    if st.button("Atualizar Número"):
        df_edit = get_data()
        df_edit.loc[df_edit['Comanda'] == comanda_errada, 'Comanda'] = comanda_certa
        conn.update(worksheet="Sheet1", data=df_edit)
        st.success("Alterado com sucesso!")
        st.rerun()

    st.divider()

    # --- EDITAR ITENS DE COMANDA JÁ LANÇADA ---
    st.subheader("❌ Cancelar Item de Comanda já Lançada")
    comanda_busca = st.number_input("Buscar Comanda para Corrigir:", min_value=1, step=1)
    
    df_db = get_data()
    if not df_db.empty:
        df_db['Comanda'] = pd.to_numeric(df_db['Comanda'], errors='coerce')
        itens_comanda = df_db[df_db['Comanda'] == comanda_busca]
        
        if not itens_comanda.empty:
            st.write(f"Itens encontrados na Comanda #{comanda_busca}:")
            for idx, row in itens_comanda.iterrows():
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(row['Item'])
                c2.write(f"R$ {row['Preço']:.2f}")
                if c3.button("Cancelar Item", key=f"del_{idx}"):
                    # Remove a linha específica do DataFrame original usando o index
                    df_final_edit = df_db.drop(idx)
                    conn.update(worksheet="Sheet1", data=df_final_edit)
                    st.warning("Item removido da planilha!")
                    st.rerun()
        else:
            st.info("Digite um número de comanda ativa para ver os itens.")

    st.divider()
    st.subheader("🚨 Danger Zone")
    if st.button("🗑️ Resetar Hoje"):
        df_atual = get_data()
        df_atual['Data'] = pd.to_datetime(df_atual['Data'])
        df_filtrado = df_atual[df_atual['Data'].dt.date != datetime.now().date()]
        conn.update(worksheet="Sheet1", data=df_filtrado)
        st.rerun()
