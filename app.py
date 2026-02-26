import streamlit as st
from services.auth import login, sign_up, check_auth
from utils.components import inject_custom_css

st.set_page_config(page_title="MedResidency Pro", page_icon="🧬", layout="wide")
inject_custom_css()

if not check_auth():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align:center;'>🧬 MedResidency Pro</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            t1, t2 = st.tabs(["Entrar", "Cadastro"])
            with t1:
                e = st.text_input("E-mail")
                p = st.text_input("Senha", type="password")
                if st.button("Acessar", use_container_width=True):
                    if login(e, p):
                        st.rerun()
            with t2:
                n = st.text_input("Nome")
                ne = st.text_input("Novo E-mail")
                np = st.text_input("Nova Senha", type="password")
                if st.button("Criar Conta", use_container_width=True):
                    if len(np) >= 6 and ne and n:
                        ok, msg = sign_up(ne, np, n)
                        st.success(msg) if ok else st.error(msg)
else:
    st.switch_page("pages/01_Dashboard.py")
