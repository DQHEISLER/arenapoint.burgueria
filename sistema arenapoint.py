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
        return df
    except Exception as e:
        st.error(f"❌ ERRO DE CONEXÃO: {e}")
        st.stop()

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []
if 'nome_cliente' not in st.session_state:
    st.session_state.nome_cliente = ""

# --- INTERFACE ---
tab_vendas, tab_relatorios, tab_config = st.tabs(["🛒 Nova Venda", "📊 Relatórios", "⚙️ Ajustes e Config"])

with tab_vendas:
    df_vendas_atual = get_data()
    proxima_comanda = int(pd.to_numeric(df_vendas_atual['Comanda'], errors='coerce').max() or 0) + 1

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
        
        obs = st.text_input("📝 Personalizar (Sem cebola, etc):")
        
        if st.button("➕ Adicionar Item", use_container_width=True):
            nome_final_item = f"{item_nome} ({obs})" if obs else item_nome
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda,
                "Nome": st.session_state.nome_cliente if st.session_state.nome_cliente else "Avulso",
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Item": nome_final_item,
                "Preço": preco
            })
            st.rerun()

    with col2:
        st.subheader(f"📋 Comanda #{proxima_comanda}")
        if st.session_state.carrinho:
            df_c = pd.DataFrame(st.session_state.carrinho)
            for i, row in df_c.iterrows():
                c_i, c_p, c_b = st.columns([3, 1, 1])
                c_i.write(row['Item'])
                c_p.write(f"R$ {row['Preço']:.2f}")
                if c_b.button("🗑️", key=f"carrinho_{i}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()
            
            st.divider()
            if st.button("✅ FINALIZAR E SALVAR", type="primary", use_container_width=True):
                with st.spinner('Salvando...'):
                    df_online = get_data()
                    df_final = pd.concat([df_online, df_c], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=df_final)
                    st.session_state.carrinho = []
                    st.session_state.nome_cliente = ""
                    st.success("Salvo!")
                    time.sleep(1)
                    st.rerun()

with tab_relatorios:
    st.title("📊 Relatórios")
    df_rel = get_data()
    if not df_rel.empty:
        df_rel['Data'] = pd.to_datetime(df_rel['Data'])
        st.metric("Faturamento Total", f"R$ {df_rel['Preço'].sum():.2f}")
        ids = sorted(df_rel['Comanda'].unique(), reverse=True)
        for id_c in ids:
            det = df_rel[df_rel['Comanda'] == id_c]
            with st.expander(f"📦 Comanda #{int(id_c)} - {det['Nome'].iloc[0]}"):
                st.table(det[["Item", "Preço"]])

with tab_config:
    st.title("⚙️ Ajustes e Configurações")
    
    # --- FUNCIONALIDADE DE EDITAR COMANDA LANÇADA ---
    st.subheader("🔍 Editar Comanda já Lançada")
    busca_comanda = st.number_input("Digite o número da comanda para editar:", min_value=1, step=1)
    
    df_edit = get_data()
    if not df_edit.empty:
        # Filtra os itens daquela comanda
        df_edit['Comanda'] = pd.to_numeric(df_edit['Comanda'], errors='coerce')
        itens_encontrados = df_edit[df_edit['Comanda'] == busca_comanda]
        
        if not itens_encontrados.empty:
            st.info(f"Editando itens da Comanda #{busca_comanda}")
            
            # Opção 1: Mudar o número da comanda inteira
            nova_comanda_num = st.number_input("Mudar toda essa comanda para o número:", min_value=1, value=int(busca_comanda))
            if nova_comanda_num != busca_comanda:
                if st.button("Confirmar Mudança de Número"):
                    df_edit.loc[df_edit['Comanda'] == busca_comanda, 'Comanda'] = nova_comanda_num
                    conn.update(worksheet="Sheet1", data=df_edit)
                    st.success(f"Comanda #{busca_comanda} agora é #{nova_comanda_num}!")
                    time.sleep(1)
                    st.rerun()

            st.divider()
            # Opção 2: Excluir itens específicos
            st.write("Itens individuais (Clique em ❌ para remover da planilha):")
            for idx, row in itens_encontrados.iterrows():
                ca, cb, cc = st.columns([3, 1, 1])
                ca.write(row['Item'])
                cb.write(f"R$ {row['Preço']:.2f}")
                if cc.button("❌", key=f"excluir_{idx}"):
                    # Remove a linha específica usando o index original
                    df_final_pos_exclusao = df_edit.drop(idx)
                    conn.update(worksheet="Sheet1", data=df_final_pos_exclusao)
                    st.warning("Item removido do sistema!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.warning("Nenhum item encontrado com esse número de comanda.")

    st.divider()
    if st.button("🗑️ Resetar Faturamento de Hoje"):
        df_now = get_data()
        df_now['Data'] = pd.to_datetime(df_now['Data'])
        df_limpo = df_now[df_now['Data'].dt.date != datetime.now().date()]
        conn.update(worksheet="Sheet1", data=df_limpo)
        st.success("Hoje foi resetado!")
        time.sleep(1)
        st.rerun()
