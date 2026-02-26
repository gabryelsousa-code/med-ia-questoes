# --- file: services/auth.py
import streamlit as st
from services.database import get_supabase

def check_auth():
    """Verifica sessão e carrega perfil"""
    client = get_supabase()
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'profile' not in st.session_state:
        st.session_state.profile = None

    # Tenta recuperar sessão persistente (opcional, complexo no Streamlit Cloud)
    # Aqui focamos no login manual para simplicidade e segurança
    return st.session_state.user is not None

def login(email, password):
    client = get_supabase()
    try:
        auth_response = client.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = auth_response.user
        
        # Buscar perfil e role
        profile_data = client.table('profiles').select('*').eq('id', auth_response.user.id).single().execute()
        st.session_state.profile = profile_data.data
        return True
    except Exception as e:
        st.error(f"Falha no login: {e}")
        return False

def logout():
    client = get_supabase()
    client.auth.sign_out()
    st.session_state.user = None
    st.session_state.profile = None
    st.rerun()

def require_auth():
    if not check_auth():
        st.warning("Faça login para continuar.")
        st.stop()

def require_admin():
    require_auth()
    if st.session_state.profile.get('role') != 'admin':
        st.error("Acesso não autorizado.")
        st.stop()
