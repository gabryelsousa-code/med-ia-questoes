# --- file: pages/02_Banco_de_Questões.py ---
import streamlit as st
from services.auth import require_auth, logout
from services.database import run_query, get_supabase
from utils.components import question_card, inject_custom_css

st.set_page_config(layout="wide", page_title="Banco de Questões")
inject_custom_css()
require_auth()

# Inicializa a cesta de simulado no estado da sessão
if 'cesta_simulado' not in st.session_state:
    st.session_state.cesta_simulado = []

with st.sidebar:
    st.markdown(f"**Dr(a). {st.session_state.profile['full_name']}**")
    if st.button("📊 Meu Desempenho", use_container_width=True): st.switch_page("pages/01_Dashboard.py")
    if st.button("🔍 Explorar Questões", use_container_width=True): st.switch_page("pages/02_Banco_de_Questões.py")
    if st.button("📝 Meus Cadernos", use_container_width=True): st.switch_page("pages/03_Simulados.py")
    if st.button("Sair da Conta"): logout()

# --- HEADER COM STATUS DO CARRINHO ---
col_title, col_cart = st.columns([3, 1])
col_title.title("🔍 Explorar Questões")

with col_cart:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(f"**🎒 Cesta:** {len(st.session_state.cesta_simulado)} questões")
        if len(st.session_state.cesta_simulado) > 0:
            if st.button("Salvar como Caderno", type="primary", use_container_width=True):
                st.session_state.modal_salvar_simulado = True

# --- MODAL DE SALVAR CADERNO ---
if st.session_state.get('modal_salvar_simulado', False):
    with st.container(border=True):
        st.markdown("### Salvar Novo Caderno de Questões")
        nome_caderno = st.text_input("Nome do Caderno (ex: Revisão Cardio)")
        col_btn1, col_btn2 = st.columns(2)
        if col_btn1.button("Confirmar Salvar", type="primary"):
            if nome_caderno:
                client = get_supabase()
                # 1. Cria o Simulado
                novo_simulado = client.table("exams").insert({
                    "user_id": st.session_state.user.id,
                    "title": nome_caderno,
                    "mode": "treino"
                }).execute()
                exam_id = novo_simulado.data[0]['id']
                
                # 2. Insere as questões
                payload_itens = [{"exam_id": exam_id, "question_id": qid} for qid in st.session_state.cesta_simulado]
                client.table("exam_questions").insert(payload_itens).execute()
                
                # 3. Limpa a cesta
                st.session_state.cesta_simulado = []
                st.session_state.modal_salvar_simulado = False
                st.success("Caderno salvo com sucesso!")
                st.switch_page("pages/03_Simulados.py")
        if col_btn2.button("Cancelar"):
            st.session_state.modal_salvar_simulado = False
            st.rerun()
    st.markdown("---")

# --- FILTROS ---
with st.container(border=True):
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    
    @st.cache_data(ttl=600)
    def get_disciplinas():
        data, _ = run_query("questions", select="disciplina")
        return sorted(list(set([d['disciplina'] for d in data]))) if data else []
    
    opcoes_finais = ["Todas"] + get_disciplinas()
    sel_disc = c1.selectbox("Disciplina", opcoes_finais)
    sel_txt = c2.text_input("Palavra-chave no enunciado")
    page = c3.number_input("Página", min_value=1, value=1)
    buscar = c4.button("Filtrar", use_container_width=True)

limit = 15
offset = (page - 1) * limit
client = get_supabase()
query = client.table("questions").select("*", count="exact").eq("ativo", True)
if sel_disc != "Todas": query = query.eq("disciplina", sel_disc)
if sel_txt: query = query.ilike("enunciado", f"%{sel_txt}%")

res = query.range(offset, offset + limit - 1).execute()
questions = res.data

st.caption(f"Exibindo {len(questions)} de {res.count} questões encontradas.")
st.markdown("---")

# --- LISTAGEM COM CHECKBOXES ---
if not questions: 
    st.info("Nenhuma questão encontrada com estes filtros.")
else:
    # Botão Selecionar Todos da Página
    if st.button("Adicionar todas desta página à Cesta"):
        novos_ids = [q['id'] for q in questions]
        st.session_state.cesta_simulado = list(set(st.session_state.cesta_simulado + novos_ids))
        st.rerun()

    for q in questions:
        col_check, col_card = st.columns([0.5, 6])
        
        with col_check:
            st.markdown("<br><br>", unsafe_allow_html=True) # Alinhamento
            is_selected = q['id'] in st.session_state.cesta_simulado
            if st.checkbox("", value=is_selected, key=f"chk_{q['id']}"):
                if q['id'] not in st.session_state.cesta_simulado:
                    st.session_state.cesta_simulado.append(q['id'])
                    st.rerun()
            else:
                if q['id'] in st.session_state.cesta_simulado:
                    st.session_state.cesta_simulado.remove(q['id'])
                    st.rerun()

        with col_card:
            question_card(q)
