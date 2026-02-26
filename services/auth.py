# --- file: services/auth.py
import streamlit as st
from services.database import get_supabase

# ... (Mantenha as funções check_auth, login, logout, etc. que já existem) ...

def sign_up(email, password, full_name):
    """Cria novo usuário no Supabase"""
    client = get_supabase()
    try:
        # Envia metadata (full_name) para o Trigger do SQL usar na tabela profiles
        auth_response = client.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {
                "data": {"full_name": full_name}
            }
        })
        
        # Se o Supabase estiver configurado para confirmar email, o user vem, mas session é None
        if auth_response.user and auth_response.user.identities:
            return True, "Conta criada com sucesso! Se necessário, verifique seu e-mail."
        elif auth_response.user and not auth_response.user.identities:
             return False, "Este e-mail já está cadastrado."
        else:
            return False, "Erro desconhecido ao criar conta."
            
    except Exception as e:
        return False, f"Erro: {str(e)}"
