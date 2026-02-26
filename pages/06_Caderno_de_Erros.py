import streamlit as st
import pandas as pd
from datetime import datetime

from services.auth import require_auth, logout
from services.database import get_supabase
from services.exams import create_exam
from services.attempts import start_attempt
from services.categories import ensure_category
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

st.title("❌ Caderno de Erros")

client = get_supabase()
user_id = st.session_state.user.id

ans = client.table("attempt_answers") \
    .select("question_id,answered_at") \
    .eq("user_id", user_id) \
    .eq("is_correct", False) \
    .order("answered_at", desc=True) \
    .limit(5000).execute().data or []

if not ans:
    st.info("Você ainda não errou questões (ou não há dados).")
    st.stop()

df = pd.DataFrame(ans)
agg = df.groupby("question_id").agg(
    erros=("question_id","count"),
    ultimo_erro=("answered_at","max")
).reset_index()

q_ids = agg["question_id"].tolist()
qrows = client.table("questions").select("id,disciplina,assunto,enunciado,banca,ano").in_("id", q_ids).execute().data or []
dfq = pd.DataFrame(qrows)

full = agg.merge(dfq, left_on="question_id", right_on="id", how="left")

with st.container(border=True):
    c1, c2, c3, c4 = st.columns([2,2,2,2])

    disciplinas = ["Todas"] + sorted([x for x in full["disciplina"].dropna().unique().tolist()])
    bancas = ["Todas"] + sorted([x for x in full["banca"].dropna().unique().tolist()])
    anos = ["Todos"] + sorted([str(int(x)) for x in full["ano"].dropna().unique().tolist()])

    f_disc = c1.selectbox("Disciplina", disciplinas)
    f_banca = c2.selectbox("Banca", bancas)
    f_ano = c3.selectbox("Ano", anos)
    max_q = c4.number_input("Limite (lista)", min_value=5, max_value=300, value=30)

filtered = full.copy()
if f_disc != "Todas":
    filtered = filtered[filtered["disciplina"] == f_disc]
if f_banca != "Todas":
    filtered = filtered[filtered["banca"] == f_banca]
if f_ano != "Todos":
    filtered = filtered[filtered["ano"] == int(f_ano)]

order = st.radio("Ordenar por", ["Mais recentes", "Mais erradas"], horizontal=True)
if order == "Mais recentes":
    filtered = filtered.sort_values("ultimo_erro", ascending=False)
else:
    filtered = filtered.sort_values("erros", ascending=False)

st.caption(f"{len(filtered)} questões no caderno (após filtros).")

left, right = st.columns([3,2])
with left:
    list_name = st.text_input("Nome da lista", value=f"Caderno de Erros - {datetime.now().date()}")
with right:
    if st.button("📚 Criar lista com filtros", use_container_width=True):
        ids = filtered["question_id"].tolist()[: int(max_q)]
        cat_id = ensure_category(user_id, "Caderno de Erros", icon="❌")
        exam_id = create_exam(
            user_id=user_id,
            title=list_name.strip() or "Caderno de Erros",
            exam_type="lista",
            category_id=cat_id,
            mode="treino",
            question_ids=ids,
            is_generated=True
        )
        st.success("Lista criada! Indo para Listas & Simulados…")
        st.switch_page("pages/03_Listas_e_Simulados.py")

if st.button("▶️ Resolver agora (filtros)", use_container_width=True):
    ids = filtered["question_id"].tolist()[: int(max_q)]
    cat_id = ensure_category(user_id, "Caderno de Erros", icon="❌")
    exam_id = create_exam(
        user_id=user_id,
        title=(list_name.strip() or "Caderno de Erros"),
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
for _, row in filtered.head(40).iterrows():
    q = {
        "disciplina": row.get("disciplina",""),
        "assunto": row.get("assunto",""),
        "enunciado": row.get("enunciado","") or "",
        "id_original": None
    }
    col1, col2 = st.columns([6,2])
    with col1:
        question_card(q)
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.write(f"**Erros:** {int(row.get('erros',0))}")
        st.write(f"**Último:** {(str(row.get('ultimo_erro'))[:10])}")
