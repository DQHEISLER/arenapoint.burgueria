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
        
        # --- LIMPEZA DE PREÇO BLINDADA (RESOLVE O ERRO DE FLOAT) ---
        if 'Preço' in df.columns:
            def limpar_valor(v):
                # Se já for um número (float ou int), retorna ele mesmo
                if isinstance(v, (int, float)):
                    return float(v)
                
                # Se for texto, limpa caracteres de moeda e espaços
                v = str(v).replace('R$', '').strip()
                if not v or v.lower() == 'nan': 
                    return 0.0
                
                # Tratamento de padrão brasileiro: 1.200,50 -> 1200.50
                if '.' in v and ',' in v:
                    v = v.replace('.', '') # Remove ponto de milhar
                v = v.replace(',', '.')    # Troca vírgula decimal por ponto
                
                try:
                    return float(v)
                except:
                    return 0.0

            # Aplica a limpeza célula por célula com segurança
            df['Preço'] = df['Preço'].apply(limpar_valor)
        
        # Restante da limpeza técnica
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

# --- ABA 3: CONFIGURAÇÕES ---
with tab_config:
    st.title("⚙️ Ajustes e Gerenciamento")
    
    st.subheader("🛠️ Cancelar Itens Lançados")
    busca_c = st.number_input("Número da comanda para editar:", min_value=1, step=1)
    df_ajuste = get_data()
    if not df_ajuste.empty:
        itens = df_ajuste[df_ajuste['Comanda'] == busca_c]
        if not itens.empty:
            for idx, row in itens.iterrows():
                ca, cb, cc = st.columns([3, 1, 1])
                ca.write(row['Item'])
                cb.write(formatar_moeda(row['Preço']))
                if cc.button("Excluir", key=f"ajuste_{idx}"):
                    df_base = conn.read(worksheet="Sheet1", ttl=0)
                    df_nova = df_base.drop(idx)
                    conn.update(worksheet="Sheet1", data=df_nova)
                    st.cache_data.clear()
                    st.success("Removido!")
                    st.rerun()
        else:
            st.write("Comanda não encontrada.")
