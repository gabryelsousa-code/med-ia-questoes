# --- file: pages/03_Simulados.py ---
import streamlit as st
from services.auth import require_auth, logout
from services.database import run_query, get_supabase
from utils.components import inject_custom_css

st.set_page_config(layout="wide", page_title="Meus Cadernos")
inject_custom_css()
require_auth()

with st.sidebar:
    st.markdown(f"**Dr(a). {st.session_state.profile['full_name']}**")
    if st.button("📊 Meu Desempenho", use_container_width=True): st.switch_page("pages/01_Dashboard.py")
    if st.button("🔍 Explorar Questões", use_container_width=True): st.switch_page("pages/02_Banco_de_Questões.py")
    if st.button("📝 Meus Cadernos", use_container_width=True): st.switch_page("pages/03_Simulados.py")
    if st.button("Sair da Conta"): logout()

st.title("📂 Meus Cadernos de Questões")

client = get_supabase()
# Buscar os cadernos do usuário
cadernos_res = client.table("exams").select("*").eq("user_id", st.session_state.user.id).order("created_at", desc=True).execute()
cadernos = cadernos_res.data

if not cadernos:
    st.info("Você ainda não possui cadernos de questões. Vá em 'Explorar Questões' e selecione questões para criar um.")
else:
    for caderno in cadernos:
        with st.container(border=True):
            col_info, col_acao = st.columns([4, 1])
            
            with col_info:
                st.markdown(f"### {caderno['title']}")
                data_criacao = caderno['created_at'][:10]
                st.caption(f"Criado em: {data_criacao}")
            
            with col_acao:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("▶️ Resolver Caderno", key=f"play_{caderno['id']}", type="primary", use_container_width=True):
                    # Criar a tentativa (Attempt)
                    att_res = client.table("attempts").insert({
                        "user_id": st.session_state.user.id,
                        "exam_id": caderno['id']
                    }).execute()
                    
                    st.session_state.active_attempt_id = att_res.data[0]['id']
                    st.session_state.current_q_idx = 0
                    st.switch_page("pages/04_Resolver.py")
                
                if st.button("🗑️ Excluir", key=f"del_{caderno['id']}", use_container_width=True):
                    client.table("exams").delete().eq("id", caderno['id']).execute()
                    st.rerun()
