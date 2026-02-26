# --- file: pages/01_Dashboard.py
import streamlit as st
from services.auth import require_auth, logout
from services.database import run_query
import pandas as pd
import plotly.express as px

require_auth()

# Sidebar Global
with st.sidebar:
    st.write(f"Olá, **{st.session_state.profile['full_name']}**")
    if st.button("Sair"): logout()

st.title("📊 Painel de Performance")

# Métricas Rápidas
user_id = st.session_state.user.id
attempts_data, _ = run_query("attempts", filters={"user_id": user_id, "status": "completed"})
answers_data, _ = run_query("attempt_answers", select="is_correct, question_id", 
                            filters={"attempt_id": [a['id'] for a in attempts_data] if attempts_data else []})

if not answers_data:
    st.info("Bem-vindo! Comece criando um simulado ou resolvendo questões.")
else:
    df = pd.DataFrame(answers_data)
    total_q = len(df)
    acertos = df['is_correct'].sum()
    taxa = (acertos/total_q)*100
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Questões Resolvidas", total_q)
    c2.metric("Acertos Totais", acertos)
    c3.metric("Taxa Global", f"{taxa:.1f}%")
    
    # Gráfico simples de evolução ou disciplina poderia vir aqui
    st.markdown("---")
    st.subheader("Atalhos")
    c_a, c_b = st.columns(2)
    if c_a.button("🚀 Criar Novo Simulado", use_container_width=True):
        st.switch_page("pages/03_Simulados.py")
    if c_b.button("🔄 Revisão Diária (Leitner)", use_container_width=True):
        st.switch_page("pages/04_Revisão_Inteligente.py")
