# --- file: pages/04_Resolver.py
import streamlit as st
from services.auth import require_auth
from services.database import get_supabase
import time

require_auth()

if 'active_attempt_id' not in st.session_state:
    st.warning("Nenhum simulado ativo.")
    if st.button("Voltar"): st.switch_page("pages/03_Simulados.py")
    st.stop()

# Carregar dados da tentativa
client = get_supabase()
attempt_id = st.session_state.active_attempt_id

# Carregar Questões da Tentativa (Join complexo precisa de view ou lógica python)
# Simplificação: Buscar IDs do exam vinculado à attempt
att_data = client.table("attempts").select("exam_id, status").eq("id", attempt_id).single().execute()
if att_data.data['status'] == 'completed':
    st.success("Simulado Finalizado!")
    # Aqui mostraria o relatório de desempenho
    if st.button("Voltar"): st.switch_page("pages/01_Dashboard.py")
    st.stop()

exam_id = att_data.data['exam_id']
q_ids_res = client.table("exam_questions").select("question_id").eq("exam_id", exam_id).execute()
q_ids = [x['question_id'] for x in q_ids_res.data]

# Paginação local
if 'current_q_idx' not in st.session_state: st.session_state.current_q_idx = 0
idx = st.session_state.current_q_idx
total = len(q_ids)

# Carregar a questão atual completa
q_data = client.table("questions").select("*").eq("id", q_ids[idx]).single().execute()
q = q_data.data

# UI da Questão
progress = (idx + 1) / total
st.progress(progress, text=f"Questão {idx + 1} de {total}")

st.markdown(f"### {q['disciplina']} | {q.get('assunto', '')}")
st.write(q['enunciado'])

# Resposta
options = q['alternativas'] # Dict {"A": "Txt"}
selected_opt = st.radio("Alternativa:", list(options.keys()), format_func=lambda x: f"{x}) {options[x]}")

c1, c2 = st.columns([1, 1])

if c1.button("Confirmar Resposta"):
    is_correct = (selected_opt == q['gabarito'])
    
    # Salvar resposta
    client.table("attempt_answers").upsert({
        "attempt_id": attempt_id,
        "question_id": q['id'],
        "user_answer": selected_opt,
        "is_correct": is_correct
    }, on_conflict="attempt_id, question_id").execute()
    
    # Feedback imediato (se modo treino)
    if is_correct:
        st.success("Correto!")
        # Atualizar Leitner aqui (via services/leitner.py)
    else:
        st.error(f"Incorreto. Gabarito: {q['gabarito']}")
        with st.expander("Comentário"):
            st.json(q.get('comentario_estruturado'))

if c2.button("Próxima" if idx < total - 1 else "Finalizar"):
    if idx < total - 1:
        st.session_state.current_q_idx += 1
        st.rerun()
    else:
        client.table("attempts").update({"status": "completed", "finished_at": "now()"}).eq("id", attempt_id).execute()
        st.balloons()
        st.rerun()
