import time
import streamlit as st

from services.auth import require_auth, logout
from services.database import get_supabase
from services.attempts import (
    get_attempt,
    set_current_index,
    finish_attempt,
    upsert_answer,
    get_attempt_answers,
)
from services.exams import get_exam
from services.leitner import update_leitner
from utils.components import inject_custom_css

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

st.title("🧠 Resolver")

client = get_supabase()
user_id = st.session_state.user.id

attempt_id = st.session_state.get("active_attempt_id")
if not attempt_id:
    st.error("Nenhuma tentativa ativa. Vá em Listas & Simulados.")
    st.stop()

attempt = get_attempt(attempt_id)
if not attempt:
    st.error("Tentativa não encontrada.")
    st.stop()

exam_id = attempt.get("exam_id")
exam = get_exam(exam_id) if exam_id else None

question_order = attempt.get("question_order") or []
if not question_order:
    st.error("Tentativa sem question_order. (Verifique a migração do attempts.question_order).")
    st.stop()

idx = attempt.get("current_index") or 0
idx = max(0, min(idx, len(question_order) - 1))

# carregar questões em batch
res = client.table("questions").select("*").in_("id", question_order).execute()
q_map = {q["id"]: q for q in (res.data or [])}
questions = [q_map[qid] for qid in question_order if qid in q_map]

# respostas atuais
answers = get_attempt_answers(attempt_id)
ans_map = {a["question_id"]: a for a in answers}

# header meta
meta_cols = st.columns([6, 2, 2])
with meta_cols[0]:
    if exam:
        st.markdown(f"**{(exam.get('exam_type') or '').upper()}** • {exam.get('title','')}")
        st.caption(f"Modo: {exam.get('mode','treino')}")
    else:
        st.markdown("**Treino avulso**")

with meta_cols[1]:
    st.metric("Progresso", f"{idx+1}/{len(questions)}")
with meta_cols[2]:
    done = sum(1 for a in answers if a.get("user_answer") is not None)
    st.metric("Respondidas", done)

st.progress((idx + 1) / len(questions))

q = questions[idx]
qid = q["id"]

# timer por questão
if "q_start_ts" not in st.session_state or st.session_state.get("q_start_qid") != qid:
    st.session_state.q_start_ts = time.time()
    st.session_state.q_start_qid = qid

# render questão
st.markdown(f"""
<div class="card-container">
  <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:10px;">
    <div>
      <span class="tag-pill">🩺 {q.get('disciplina','')}</span>
      <span class="small-muted">{q.get('assunto') or ''}</span>
    </div>
    <span class="small-muted">ID: {q.get('id_original') or 'N/A'}</span>
  </div>
  <div class="enunciado">{q.get('enunciado','')}</div>
</div>
""", unsafe_allow_html=True)

alts = q.get("alternativas") or {}
letters = sorted(list(alts.keys()), key=lambda x: x.upper())
opts = [f"{L}) {alts[L]}" for L in letters]

prev = (ans_map.get(qid) or {}).get("user_answer")
default_idx = None
if prev:
    for i, o in enumerate(opts):
        if o.startswith(prev + ")"):
            default_idx = i
            break

choice = st.radio("Alternativas", opts, index=default_idx, label_visibility="collapsed")

# navegação helper
def go_to(new_idx: int):
    new_idx = max(0, min(new_idx, len(questions) - 1))
    set_current_index(attempt_id, new_idx)
    st.rerun()

# ações
a1, a2, a3, a4 = st.columns([1.2, 2.2, 1.2, 1.6])

with a1:
    if st.button("⬅️ Anterior", use_container_width=True, disabled=(idx == 0)):
        go_to(idx - 1)

with a2:
    if st.button("✅ Confirmar", use_container_width=True):
        letter = choice.split(")")[0].strip().upper()
        gab = (q.get("gabarito") or "").strip().upper()
        is_correct = (letter == gab) if gab else None
        elapsed = int(time.time() - st.session_state.q_start_ts)

        upsert_answer(
            user_id=user_id,
            attempt_id=attempt_id,
            question_id=qid,
            user_answer=letter,
            is_correct=is_correct,
            time_spent_seconds=elapsed
        )

        # Leitner
        if is_correct is not None:
            update_leitner(user_id, qid, bool(is_correct))

        st.session_state.q_start_ts = time.time()
        st.success("Resposta registrada!")
        st.rerun()

with a3:
    if st.button("⏭️ Pular", use_container_width=True):
        elapsed = int(time.time() - st.session_state.q_start_ts)
        upsert_answer(
            user_id=user_id,
            attempt_id=attempt_id,
            question_id=qid,
            user_answer=None,
            is_correct=None,
            time_spent_seconds=elapsed
        )
        if idx < len(questions) - 1:
            go_to(idx + 1)
        else:
            st.info("Última questão.")

with a4:
    if st.button("🏁 Finalizar", use_container_width=True):
        finish_attempt(attempt_id)
        st.session_state.view_attempt_id = attempt_id
        st.success("Tentativa finalizada!")
        st.switch_page("pages/05_Resultados.py")

# feedback
a = ans_map.get(qid)
if a and a.get("user_answer") is not None:
    gab = (q.get("gabarito") or "").strip().upper()
    ua = (a.get("user_answer") or "").strip().upper()
    if gab:
        if ua == gab:
            st.success(f"✅ Correto! Gabarito: {gab}")
        else:
            st.error(f"❌ Incorreto. Seu: {ua} | Gabarito: {gab}")

# comentário
ce = q.get("comentario_estruturado")
if ce:
    with st.expander("📌 Comentário / Explicação"):
        if isinstance(ce, dict):
            st.write(ce.get("fundamentacao_cientifica") or "")
            corr = (ce.get("justificativa_alternativa_correta") or {})
            if corr:
                st.markdown("**Justificativa da correta:**")
                st.write(corr.get("explicacao") or "")
        else:
            st.write(ce)

if st.button("Próxima ➡️", use_container_width=True, disabled=(idx == len(questions) - 1)):
    go_to(idx + 1)
