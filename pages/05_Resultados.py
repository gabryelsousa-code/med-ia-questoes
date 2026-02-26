import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from services.auth import require_auth, logout
from services.database import get_supabase
from services.attempts import get_attempt, get_attempt_answers, start_attempt
from services.exams import get_exam, create_exam
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

st.title("📄 Resultados da Tentativa")

client = get_supabase()
user_id = st.session_state.user.id

attempts = client.table("attempts") \
    .select("id,exam_id,status,started_at,finished_at") \
    .eq("user_id", user_id) \
    .order("started_at", desc=True) \
    .limit(50).execute().data or []

if not attempts:
    st.info("Você ainda não tem tentativas.")
    st.stop()

# exam titles batch
exam_ids = sorted({a["exam_id"] for a in attempts if a.get("exam_id")})
exam_map = {}
if exam_ids:
    ex = client.table("exams").select("id,title,exam_type").in_("id", exam_ids).execute().data or []
    exam_map = {e["id"]: e for e in ex}

def label_attempt(a):
    ex = exam_map.get(a.get("exam_id"))
    title = ex["title"] if ex else "Treino avulso"
    typ = (ex.get("exam_type","") if ex else "").upper()
    dt = (a.get("started_at") or "")[:19].replace("T", " ")
    return f"{dt} • {typ} {title} • {a.get('status')}"

default_id = st.session_state.get("view_attempt_id") or attempts[0]["id"]
ids = [a["id"] for a in attempts]
default_idx = ids.index(default_id) if default_id in ids else 0

attempt_id = st.selectbox(
    "Selecionar tentativa",
    ids,
    index=default_idx,
    format_func=lambda x: label_attempt(next(a for a in attempts if a["id"] == x))
)
st.session_state.view_attempt_id = attempt_id

attempt = get_attempt(attempt_id)
answers = get_attempt_answers(attempt_id)

question_order = attempt.get("question_order") or []
total = len(question_order)

df_ans = pd.DataFrame(answers) if answers else pd.DataFrame(columns=["question_id","user_answer","is_correct","time_spent_seconds"])
answered = int((df_ans["user_answer"].notna()).sum()) if not df_ans.empty else 0
correct = int((df_ans["is_correct"] == True).sum()) if not df_ans.empty else 0
wrong   = int((df_ans["is_correct"] == False).sum()) if not df_ans.empty else 0
blank   = total - answered
acc = (correct / answered) * 100 if answered > 0 else 0.0
total_time = int(df_ans["time_spent_seconds"].fillna(0).sum()) if not df_ans.empty else 0
avg_time = (total_time / answered) if answered > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total", total)
c2.metric("Respondidas", answered)
c3.metric("Acertos", correct)
c4.metric("Aproveitamento", f"{acc:.1f}%")

c5, c6, c7 = st.columns(3)
c5.metric("Erros", wrong)
c6.metric("Em branco", blank)
c7.metric("Tempo médio (s)", f"{avg_time:.0f}")

# batch load question metadata
q_map = {}
if question_order:
    qrows = client.table("questions").select("id,disciplina,assunto,enunciado,banca,ano").in_("id", question_order).execute().data or []
    q_map = {q["id"]: q for q in qrows}

colA, colB = st.columns(2)

with colA:
    fig = go.Figure(data=[go.Pie(labels=["Acertos", "Erros", "Em branco"], values=[correct, wrong, blank], hole=0.55)])
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig, use_container_width=True)

with colB:
    if not df_ans.empty and q_map:
        df_q = pd.DataFrame([q_map[qid] for qid in question_order if qid in q_map])
        df = df_ans.merge(df_q, left_on="question_id", right_on="id", how="left")
        g = df.groupby("disciplina").agg(
            Total=("question_id","count"),
            Respondidas=("user_answer", lambda s: s.notna().sum()),
            Acertos=("is_correct", lambda s: (s==True).sum())
        ).reset_index()
        g["Taxa (%)"] = g.apply(lambda r: (r["Acertos"]/r["Respondidas"]*100) if r["Respondidas"]>0 else 0, axis=1)
        fig2 = px.bar(g.sort_values("Taxa (%)"), x="Taxa (%)", y="disciplina", orientation="h", text_auto=".1f")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sem dados suficientes para gráfico por disciplina.")

st.markdown("---")
st.subheader("❌ Questões erradas")

wrong_ids = []
if not df_ans.empty:
    wrong_ids = df_ans[df_ans["is_correct"] == False]["question_id"].tolist()

if not wrong_ids:
    st.success("Nenhuma questão errada nesta tentativa 🎉")
else:
    left, right = st.columns([3,1])
    with left:
        list_name = st.text_input("Nome da lista de revisão", value=f"Caderno de Erros - {datetime.now().date()}")
    with right:
        if st.button("📚 Criar lista com erradas", use_container_width=True):
            cat_id = ensure_category(user_id, "Caderno de Erros", icon="❌")
            exam_id = create_exam(
                user_id=user_id,
                title=list_name.strip() or "Caderno de Erros",
                exam_type="lista",
                category_id=cat_id,
                mode="treino",
                question_ids=list(dict.fromkeys(wrong_ids)),
                is_generated=True
            )
            st.success("Lista criada! Indo para Listas & Simulados…")
            st.switch_page("pages/03_Listas_e_Simulados.py")

    if st.button("▶️ Resolver erradas agora", use_container_width=True):
        ids = list(dict.fromkeys(wrong_ids))
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
        attempt_new = start_attempt(user_id, exam_id, question_order=ids)
        st.session_state.active_attempt_id = attempt_new
        st.switch_page("pages/04_Resolver.py")

    for qid in wrong_ids[:40]:
        q = q_map.get(qid, {"enunciado":"Questão não encontrada", "disciplina":"", "assunto":""})
        col1, col2 = st.columns([6,2])
        with col1:
            question_card(q)
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.write("➡️ Use o Banco para selecionar e criar listas também.")
