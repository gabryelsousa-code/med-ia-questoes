# --- file: app.py
import streamlit as st
from services.auth import login, check_auth
from utils.components import inject_custom_css

st.set_page_config(page_title="MedResidency Pro", page_icon="🧬", layout="wide")
inject_custom_css()

# Tela de Login Principal
if not check_auth():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align:center; color:#002855;'>🧬 MedResidency Pro</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;'>Plataforma de Alta Performance</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            tab1, tab2 = st.tabs(["Entrar", "Cadastro"])
            with tab1:
                email = st.text_input("E-mail")
                password = st.text_input("Senha", type="password")
                if st.button("Acessar", use_container_width=True):
                    if login(email, password):
                        st.rerun()
            with tab2:
                # --- CÓDIGO NOVO DE CADASTRO ---
                new_name = st.text_input("Nome Completo")
                new_email = st.text_input("E-mail para cadastro")
                new_password = st.text_input("Senha (mín. 6 caracteres)", type="password")
                
                if st.button("Criar Conta", use_container_width=True):
                    if len(new_password) < 6:
                        st.error("A senha precisa ter pelo menos 6 caracteres.")
                    elif not new_email or not new_name:
                        st.error("Preencha todos os campos.")
                    else:
                        # Importando a função nova aqui
                        from services.auth import sign_up 
                        
                        sucesso, mensagem = sign_up(new_email, new_password, new_name)
                        if sucesso:
                            st.success(mensagem)
                            st.info("Agora faça login na aba 'Entrar'.")
                        else:
                            st.error(mensagem)

else:
    # Redireciona para Dashboard se estiver logado
    st.switch_page("pages/01_Dashboard.py")
