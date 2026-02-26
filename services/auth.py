import streamlit as st
from services.database import get_supabase

def check_auth():
    if "user" not in st.session_state:
        st.session_state.user = None
    if "profile" not in st.session_state:
        st.session_state.profile = None
    return st.session_state.user is not None

def login(email, password):
    client = get_supabase()
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        if res.user:
            try:
                prof = client.table("profiles").select("*").eq("id", res.user.id).single().execute()
                st.session_state.profile = prof.data
            except:
                st.session_state.profile = {"role": "user", "full_name": "Usuário"}
        return True
    except Exception:
        st.error("Falha no login.")
        return False

def sign_up(email, password, full_name):
    client = get_supabase()
    try:
        res = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name}}
        })
        if res.user:
            return True, "Conta criada! Faça login."
        return False, "Erro ao criar."
    except Exception as e:
        return False, f"Erro: {e}"

def logout():
    client = get_supabase()
    client.auth.sign_out()
    st.session_state.user = None
    st.session_state.profile = None
    st.rerun()

def require_auth():
    if not check_auth():
        st.warning("Faça login.")
        st.stop()
