import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arena Point - Sistema Estável", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO DE LEITURA SEGURA (IMPEDE RESET) ---
def get_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty and len(df.columns) < 2):
            return pd.DataFrame(columns=["Comanda", "Nome", "Data", "Item", "Preço"])
        return df
    except Exception as e:
        st.error(f"❌ ERRO DE CONEXÃO: Não foi possível ler a planilha. Verifique a internet. Detalhe: {e}")
        st.stop() # Interrompe o código para evitar que salve dados vazios por cima

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []
if 'nome_cliente' not in st.session_state:
    st.session_state.nome_cliente = ""

# --- INTERFACE POR ABAS ---
tab_vendas, tab_relatorios, tab_config = st.tabs(["🛒 Nova Venda", "📊 Relatórios", "⚙️ Ajustes e Config"])

with tab_vendas:
    # Lógica de número de comanda puxando dado fresco
    df_vendas_atual = get_data()
    if not df_vendas_atual.empty:
        df_vendas_atual['Comanda'] = pd.to_numeric(df_vendas_atual['Comanda'], errors='coerce')
        proxima_comanda = int(df_vendas_atual['Comanda'].max() or 0) + 1
    else:
        proxima_comanda = 1

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
        
        # NOVO: CAMPO PARA ADICIONAR OU RETIRAR ALGO
        obs = st.text_input("📝 Personalizar (Ex: Sem cebola / + Bacon):", placeholder="Opcional")
        
        if st.button("➕ Adicionar Item", use_container_width=True):
            cliente_final = st.session_state.nome_cliente if st.session_state.nome_cliente else "Cliente Avulso"
            # Salva o item com a observação se ela existir
            nome_final_item = f"{item_nome} ({obs})" if obs else item_nome
            
            st.session_state.carrinho.append({
                "Comanda": proxima_comanda,
                "Nome": cliente_final,
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Item": nome_final_item,
                "Preço": preco
            })
            st.toast(f"Adicionado: {nome_final_item}")
            st.rerun()

    with col2:
        st.subheader(f"📋 Comanda #{proxima_comanda}")
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            
            # Lista de itens com botão remover
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
                with st.spinner('Salvando no Google Sheets... Aguarde.'):
                    # Passo 1: Lê o dado mais recente para evitar conflito
                    df_online = get_data()
                    # Passo 2: Junta os dados
                    df_final = pd.concat([df_online, df_cart], ignore_index=True)
                    # Passo 3: Tenta salvar
                    try:
                        conn.update(worksheet="Sheet1", data=df_final)
                        st.session_state.carrinho = []
                        st.session_state.nome_cliente = ""
                        st.success("Pedido salvo com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
        else:
            st.info("Adicione itens para começar.")

# --- ABAS DE RELATÓRIO E CONFIGURAÇÃO (MANTIDAS) ---
with tab_relatorios:
    st.title("📊 Relatórios")
    df_vendas = get_data()
    if not df_vendas.empty:
        df_vendas['Data'] = pd.to_datetime(df_vendas['Data'])
        hoje = datetime.now().date()
        fatur_dia = df_vendas[df_vendas['Data'].dt.date == hoje]['Preço'].sum()
        st.metric("Faturamento Hoje", f"R$ {fatur_dia:.2f}")
        
        st.divider()
        ids = sorted(df_vendas['Comanda'].unique(), reverse=True)
        for id_c in ids:
            detalhe = df_vendas[df_vendas['Comanda'] == id_c]
            with st.expander(f"📦 Comanda #{int(id_c)} - {detalhe['Nome'].iloc[0]}"):
                st.table(detalhe[["Item", "Preço"]])
                st.write(f"**Total: R$ {detalhe['Preço'].sum():.2f}**")

with tab_config:
    st.title("⚙️ Ajustes")
    # ... (Botões de correção de número e cancelar item se mantêm aqui)
    st.info("Use esta aba para correções pontuais em comandas já fechadas.")
