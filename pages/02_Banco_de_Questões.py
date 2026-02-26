# --- file: pages/02_Banco_de_Questões.py
import streamlit as st
from services.auth import require_auth
from services.database import run_query, get_supabase
from utils.components import question_card

require_auth()
st.title("🔍 Explorar Questões")

# --- Interface de Filtros ---
with st.container(border=True):
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    
    @st.cache_data(ttl=600)
    def get_disciplinas():
        data, _ = run_query("questions", select="disciplina")
        return sorted(list(set([d['disciplina'] for d in data]))) if data else []
    
    # Adicionando opções padrão baseadas em áreas comuns de residência
    disciplinas_banco = get_disciplinas()
    opcoes_disc = ["Todas", "Doenças Infecciosas", "Neurologia", "Ortopedia", "Cirurgia Geral", "Clínica Médica"]
    opcoes_finais = sorted(list(set(opcoes_disc + disciplinas_banco)))
    if "Todas" in opcoes_finais: opcoes_finais.remove("Todas")
    opcoes_finais.insert(0, "Todas")

    sel_disc = c1.selectbox("Disciplina", opcoes_finais)
    sel_txt = c2.text_input("Palavra-chave no enunciado")
    
    # Botão de busca e Paginação
    buscar = c4.button("Filtrar", use_container_width=True)
    page = c3.number_input("Página", min_value=1, value=1)

limit = 15
offset = (page - 1) * limit

# --- Execução da Query ---
client = get_supabase()
query = client.table("questions").select("*", count="exact").eq("ativo", True)

if sel_disc != "Todas": 
    query = query.eq("disciplina", sel_disc)
if sel_txt: 
    query = query.ilike("enunciado", f"%{sel_txt}%")

res = query.range(offset, offset + limit - 1).execute()
questions = res.data
total_count = res.count

st.caption(f"Exibindo {len(questions)} de {total_count} questões encontradas.")
st.markdown("---")

# --- Listagem de Questões com Ação ---
if not questions:
    st.info("Nenhuma questão encontrada com estes filtros.")
else:
    for q in questions:
        col_card, col_action = st.columns([5, 1])
        
        with col_card:
            question_card(q)
            
        with col_action:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if st.button("📝 Resolver", key=f"btn_res_{q['id']}", use_container_width=True):
                # Prepara o estado para a página de resolução
                st.session_state.questoes_carregadas = [q]
                st.session_state.current_q_idx = 0
                st.session_state.active_attempt_id = "avulso" # Flag para modo estudo livre
                st.switch_page("pages/04_Resolver.py")
