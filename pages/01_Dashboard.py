import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from services.auth import require_auth, logout
from services.database import get_supabase
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

st.title("📈 Meu Desempenho Global")
client = get_supabase()
user_id = st.session_state.user.id

ans = client.table("attempt_answers").select("question_id,is_correct,answered_at,user_answer,time_spent_seconds").eq("user_id", user_id).order("answered_at", desc=True).limit(20000).execute().data or []
if not ans:
    st.info("Comece a resolver questões para ver seus gráficos.")
    st.stop()

df_ans = pd.DataFrame(ans)
df_ans["answered_at"] = pd.to_datetime(df_ans["answered_at"], errors="coerce")
df_ans["date"] = df_ans["answered_at"].dt.date
df_ans["answered"] = df_ans["user_answer"].notna()

q_ids = list(set(df_ans["question_id"].tolist()))
q = client.table("questions").select("id,disciplina").in_("id", q_ids).execute().data or []
df_q = pd.DataFrame(q)
df = df_ans.merge(df_q, left_on="question_id", right_on="id", how="left")

tot_resp = int(df["answered"].sum())
tot_acert = int((df["is_correct"] == True).sum())
tot_erro = int((df["is_correct"] == False).sum())
taxa = (tot_acert / tot_resp * 100) if tot_resp > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Respondidas", tot_resp)
c2.metric("Acertos", tot_acert)
c3.metric("Erros", tot_erro)
c4.metric("Aproveitamento", f"{taxa:.1f}%")

colA, colB = st.columns(2)

with colA:
    fig_donut = go.Figure(data=[go.Pie(labels=['Acertos', 'Erros'], values=[tot_acert, tot_erro], hole=.55)])
    fig_donut.update_layout(margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig_donut, use_container_width=True)

with colB:
    df_disc = df.groupby('disciplina').agg(Total=('answered', 'sum'), Acertos=('is_correct', lambda s: (s==True).sum())).reset_index()
    df_disc["Taxa (%)"] = df_disc.apply(lambda r: (r["Acertos"]/r["Total"]*100) if r["Total"]>0 else 0, axis=1)
    fig_bar = px.bar(df_disc.sort_values('Taxa (%)'), x='Taxa (%)', y='disciplina', orientation='h', text_auto='.1f')
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")
st.subheader("📆 Evolução (últimos 90 dias)")

d90 = df[df["date"] >= (pd.Timestamp.today().date() - pd.Timedelta(days=90))]
daily = d90.groupby("date").agg(
    Respondidas=("answered", "sum"),
    Acertos=("is_correct", lambda s: (s==True).sum()),
).reset_index()
daily["Taxa (%)"] = daily.apply(lambda r: (r["Acertos"]/r["Respondidas"]*100) if r["Respondidas"]>0 else 0, axis=1)

if not daily.empty:
    fig1 = px.line(daily, x="date", y="Respondidas")
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(daily, x="date", y="Taxa (%)")
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Sem dados nos últimos 90 dias.")
