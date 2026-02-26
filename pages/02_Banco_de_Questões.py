import streamlit as st
from services.auth import require_auth, logout
from services.database import get_supabase
from services.categories import list_categories, create_category, ensure_default_category
from services.exams import create_exam
from services.attempts import start_attempt
from services.interactions import get_interactions_map, set_favorite
from utils.components import question_card, inject_custom_css

st.set_page_config(layout="wide")
inject_custom_css()
require_auth()

with st.sidebar:
    st.markdown(f"**Dr(a). {st.session_state.profile['full_name']}**")
    if st.button("📊 Meu Desempenho", use_container_width=True): st.switch_page("pages/01_Dashboard.py")
    if st.button("🔍 Banco de Questões", use_container_width=True): st.switch_page("pages/02_Banco_de_Questoes.py")
    if st.button("🗂️ Listas & Simulados", use_container_width=True): st.switch_page("pages/03_Listas_e_Simulados.py")
    if st.button("❌ Caderno de Erros", use_container_width=True): st.switch_page("pages/06_Caderno_de_Erros.py")
    if st.button("📌 Revisão do Dia", use_container_width=True): st.switch_page("pages/07_Revisao_do_Dia.py")
    if st.session_state.profile.get("role") == "admin":
        if st.button("⚙️ Administração", use_container_width=True): st.switch_page("pages/99_Painel_Admin.py")
    if st.button("Sair da Conta"): logout()

st.title("🔍 Banco de Questões")
client = get_supabase()
user_id = st.session_state.user.id

if "selected_qids" not in st.session_state:
    st.session_state.selected_qids = []

default_cat_id = ensure_default_category(user_id)
cats = list_categories(user_id)
cat_items = [(c["id"], f"{(c.get('icon') or '📁')} {c['name']}") for c in cats]
cat_ids = [x[0] for x in cat_items]
cat_labels = [x[1] for x in cat_items]

with st.container(border=True):
    c1, c2, c3, c4, c5 = st.columns([2,2,2,1,1])

    r = client.table("questions").select("disciplina,banca,ano").eq("ativo", True).limit(2000).execute()
    data = r.data or []
    disciplinas = sorted({d["disciplina"] for d in data if d.get("disciplina")})
    bancas = sorted({d["banca"] for d in data if d.get("banca")})
    anos = sorted({d["ano"] for d in data if d.get("ano")})

    sel_disc = c1.selectbox("Disciplina", ["Todas"] + disciplinas)
    sel_banca = c2.selectbox("Banca", ["Todas"] + bancas)
    sel_ano = c3.selectbox("Ano", ["Todos"] + [str(a) for a in anos])
    sel_txt = c4.text_input("Busca")
    page = c5.number_input("Página", min_value=1, value=1)

limit = 12
offset = (page - 1) * limit

query = client.table("questions").select("*", count="exact").eq("ativo", True)
if sel_disc != "Todas": query = query.eq("disciplina", sel_disc)
if sel_banca != "Todas": query = query.eq("banca", sel_banca)
if sel_ano != "Todos": query = query.eq("ano", int(sel_ano))
if sel_txt: query = query.ilike("enunciado", f"%{sel_txt}%")

res = query.range(offset, offset + limit - 1).execute()
questions = res.data or []
total = res.count or 0

st.markdown(f"""
<div class="toolbar">
  <b>Selecionadas:</b> {len(st.session_state.selected_qids)} questões
  <span class="small-muted" style="margin-left:10px;">→ salve como Lista/Simulado em uma Categoria</span>
</div>
""", unsafe_allow_html=True)

t1, t2, t3, t4, t5 = st.columns([2.5, 1.3, 2.2, 2.0, 1.0])
title = t1.text_input("Nome", placeholder="Ex: Cardio - Semana 1", label_visibility="collapsed")
exam_type_label = t2.radio("Tipo", ["Lista", "Simulado"], horizontal=True, label_visibility="collapsed")
exam_type = "lista" if exam_type_label == "Lista" else "simulado"

selected_cat_idx = t3.selectbox("Categoria", list(range(len(cat_labels))) if cat_labels else [], format_func=lambda i: cat_labels[i]) if cat_labels else None
selected_cat_id = cat_ids[selected_cat_idx] if selected_cat_idx is not None else None

with t3:
    with st.expander("➕ Nova categoria"):
        new_cat_name = st.text_input("Nome da categoria", key="new_cat_name")
        new_cat_icon = st.text_input("Ícone (emoji)", value="📁", key="new_cat_icon")
        if st.button("Criar categoria", use_container_width=True):
            if new_cat_name.strip():
                create_category(user_id, new_cat_name.strip(), icon=new_cat_icon.strip() or "📁")
                st.success("Categoria criada!")
                st.rerun()

save_disabled = (len(st.session_state.selected_qids) == 0 or not title.strip())
solve_disabled = (len(st.session_state.selected_qids) == 0)

if t4.button("💾 Salvar", use_container_width=True, disabled=save_disabled):
    create_exam(user_id, title.strip(), exam_type, selected_cat_id, "treino", st.session_state.selected_qids, is_generated=False)
    st.session_state.selected_qids = []
    st.success("Salvo com sucesso!")
    st.switch_page("pages/03_Listas_e_Simulados.py")

if t5.button("▶️ Resolver", use_container_width=True, disabled=solve_disabled):
    exam_id = create_exam(user_id, title.strip() or "Treino rápido", exam_type, selected_cat_id, "treino", st.session_state.selected_qids, is_generated=False)
    attempt_id = start_attempt(user_id, exam_id, question_order=st.session_state.selected_qids)
    st.session_state.active_attempt_id = attempt_id
    st.switch_page("pages/04_Resolver.py")

if st.button("🧹 Limpar seleção", use_container_width=True, disabled=(len(st.session_state.selected_qids) == 0)):
    st.session_state.selected_qids = []
    st.rerun()

st.caption(f"Exibindo {len(questions)} de {total} questões.")
st.markdown("---")

if not questions:
    st.info("Nada encontrado.")
    st.stop()

page_qids = [q["id"] for q in questions]
inter_map = get_interactions_map(user_id, page_qids)

for q in questions:
    qid = q["id"]
    is_fav = bool((inter_map.get(qid) or {}).get("is_favorite"))

    col_c, col_actions = st.columns([6.5, 2.5])
    with col_c:
        question_card(q)
    with col_actions:
        st.markdown("<br>", unsafe_allow_html=True)
        selected = (qid in st.session_state.selected_qids)
        new_val = st.checkbox("Selecionar", value=selected, key=f"sel_{qid}")
        if new_val and not selected:
            st.session_state.selected_qids.append(qid)
        if (not new_val) and selected:
            st.session_state.selected_qids.remove(qid)

        fav_label = "⭐ Favorita" if is_fav else "☆ Favoritar"
        if st.button(fav_label, key=f"fav_{qid}", use_container_width=True):
            set_favorite(user_id, qid, not is_fav)
            st.rerun()
