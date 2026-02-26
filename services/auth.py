import streamlit as st
from services.database import get_supabase

def check_auth():
    """Verifica sessão e carrega perfil"""
    client = get_supabase()
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'profile' not in st.session_state:
        st.session_state.profile = None

    return st.session_state.user is not None

def login(email, password):
    client = get_supabase()
    try:
        auth_response = client.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = auth_response.user
        
        # Buscar perfil
        if auth_response.user:
            try:
                profile_data = client.table('profiles').select('*').eq('id', auth_response.user.id).single().execute()
                st.session_state.profile = profile_data.data
            except:
                st.session_state.profile = {"role": "user", "full_name": "Usuário"} # Fallback
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

def sign_up(email, password, full_name):
    client = get_supabase()
    try:
        auth_response = client.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {
                "data": {"full_name": full_name}
            }
        })
        if auth_response.user:
            return True, "Conta criada! Faça login."
        return False, "Erro ao criar conta."
    except Exception as e:
        return False, f"Erro: {str(e)}"

def require_auth():
    if not check_auth():
        st.warning("Faça login para continuar.")
        st.stop()

def require_admin():
    require_auth()
    # Verifica se tem perfil e se é admin
    if st.session_state.profile and st.session_state.profile.get('role') == 'admin':
        return
    st.error("Acesso não autorizado.")
    st.stop()
