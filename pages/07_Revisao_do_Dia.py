import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from services.auth import require_auth, logout
from services.database import get_supabase
from services.categories import ensure_category
from services.exams import create_exam
from services.attempts import start_attempt
from utils.components import inject_custom_css, question_card

st.set_page_config(layout="wide")
inject_custom_css()
require_auth()

with st.sidebar:
    st.markdown(f"**Dr(a). {st.session_state.profile['full_name']}**")
    st.markdown("---")
    if st.button("📊 Meu Desempenho", use_container_width=True): st.switch_page("pages/01_Dashboard.py")
    if st.button("🔍 Banco de Questões", use_container_width=True): st.switch_page("pages/02_Banco_de_Questoes.py")
    if st.button("🗂️ Listas & Simulados", use_container_width=True): st.switch_page("pages/03_Listas_e_Simulados.py")
    if st.button("❌ Caderno de Erros", use_container_width=True): st.switch_page("pages/06_Caderno_de_Erros.py")
    if st.button("📌 Revisão do Dia", use_container_width=True): st.switch_page("pages/07_Revisao_do_Dia.py")
    if st.session_state.profile.get("role") == "admin":
        if st.button("⚙️ Administração", use_container_width=True): st.switch_page("pages/99_Painel_Admin.py")
    st.markdown("---")
    if st.button("Sair da Conta"): logout()

st.title("📌 Revisão do Dia (Leitner)")

client = get_supabase()
user_id = st.session_state.user.id
now = datetime.now(timezone.utc).isoformat()

due = client.table("user_interactions") \
    .select("question_id,leitner_box,next_review_at") \
    .eq("user_id", user_id) \
    .lte("next_review_at", now) \
    .order("next_review_at") \
    .limit(80).execute().data or []

st.caption("O Leitner é atualizado quando você CONFIRMA a resposta no Resolver.")

if not due:
    st.success("Nada para revisar agora 🎉")
    st.stop()

df_due = pd.DataFrame(due)
q_ids = df_due["question_id"].tolist()

qrows = client.table("questions").select("id,disciplina,assunto,enunciado,banca,ano").in_("id", q_ids).execute().data or []
q_map = {q["id"]: q for q in qrows}

c1, c2, c3 = st.columns(3)
c1.metric("Para revisar agora", len(due))
c2.metric("Caixa média", f"{df_due['leitner_box'].fillna(0).mean():.1f}")
c3.metric("Data", str(datetime.now().date()))

with st.container(border=True):
    limit = st.number_input("Qtd. para revisar hoje", min_value=5, max_value=len(due), value=min(30, len(due)))
    title = st.text_input("Nome da sessão", value=f"Revisão do Dia - {datetime.now().date()}")

if st.button("▶️ Iniciar revisão", use_container_width=True, type="primary"):
    ids = q_ids[: int(limit)]
    cat_id = ensure_category(user_id, "Revisões", icon="📌")
    exam_id = create_exam(
        user_id=user_id,
        title=title.strip() or "Revisão do Dia",
        exam_type="lista",
        category_id=cat_id,
        mode="treino",
        question_ids=ids,
        is_generated=True
    )
    attempt_id = start_attempt(user_id, exam_id, question_order=ids)
    st.session_state.active_attempt_id = attempt_id
    st.switch_page("pages/04_Resolver.py")

st.markdown("---")
st.subheader("Prévia")
for qid in q_ids[:20]:
    q = q_map.get(qid)
    if q:
        question_card(q)
