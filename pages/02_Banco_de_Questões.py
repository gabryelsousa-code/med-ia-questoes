# --- file: pages/02_Banco_de_Questões.py
import streamlit as st
from services.auth import require_auth
from services.database import run_query, get_supabase
from utils.components import question_card

require_auth()
st.title("🔍 Banco de Questões")

# --- Filtros ---
with st.expander("Filtros de Pesquisa", expanded=True):
    c1, c2, c3 = st.columns(3)
    
    # Cache para disciplinas
    @st.cache_data
    def get_disciplinas():
        data, _ = run_query("questions", select="disciplina")
        return sorted(list(set([d['disciplina'] for d in data]))) if data else []
    
    disciplinas = get_disciplinas()
    sel_disc = c1.selectbox("Disciplina", ["Todas"] + disciplinas)
    sel_txt = c2.text_input("Buscar Texto")
    
    # Paginação
    page = c3.number_input("Página", 1, 100, 1)
    limit = 20
    offset = (page - 1) * limit

# --- Query ---
filters = {}
if sel_disc != "Todas": filters["disciplina"] = sel_disc

client = get_supabase()
query = client.table("questions").select("*", count="exact").eq("ativo", True)
if sel_disc != "Todas": query = query.eq("disciplina", sel_disc)
if sel_txt: query = query.ilike("enunciado", f"%{sel_txt}%")

res = query.range(offset, offset + limit - 1).execute()
questions = res.data
total_count = res.count

st.caption(f"Total encontrado: {total_count} | Página {page}")

# --- Lista ---
if not questions:
    st.warning("Nenhuma questão encontrada.")
else:
    for q in questions:
        question_card(q)
        # Botão para adicionar a simulado (conceitual)
        if st.button(f"Ver Detalhes/Responder", key=q['id']):
            # Em uma implementação completa, levaria para uma página de single view
            st.session_state.single_question_id = q['id']
            st.switch_page("pages/04_Resolver.py")
