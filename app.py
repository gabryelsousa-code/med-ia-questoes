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
                st.info("Entre em contato com admin para cadastro ou implemente sign_up na services/auth.py")

else:
    # Redireciona para Dashboard se estiver logado
    st.switch_page("pages/01_Dashboard.py")
