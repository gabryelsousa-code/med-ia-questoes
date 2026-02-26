# --- file: pages/01_Dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from services.auth import require_auth, logout
from services.database import run_query

require_auth()

# Sidebar Control (Com botões de navegação manuais para contornar a navbar nativa)
with st.sidebar:
    st.markdown(f"**Dr(a). {st.session_state.profile['full_name']}**")
    st.markdown("---")
    if st.button("🔍 Explorar Questões", use_container_width=True): st.switch_page("pages/02_Banco_de_Questões.py")
    if st.button("📝 Meus Simulados", use_container_width=True): st.switch_page("pages/03_Simulados.py")
    if st.button("📊 Meu Desempenho", use_container_width=True): st.switch_page("pages/01_Dashboard.py")
    if st.session_state.profile.get('role') == 'admin':
        if st.button("⚙️ Administração", use_container_width=True): st.switch_page("pages/99_Painel_Admin.py")
    st.markdown("---")
    if st.button("Sair da Conta"): logout()

st.title("📈 Meu Desempenho Global")

# --- Coleta de Dados ---
user_id = st.session_state.user.id

# Buscar todas as respostas do usuário
ans_data, _ = run_query("attempt_answers", filters={"user_id": user_id})

if not ans_data:
    st.info("Você ainda não resolveu nenhuma questão. Os gráficos aparecerão aqui quando você começar seus estudos.")
    st.stop()

# Buscar as informações das questões respondidas para cruzar os dados (Disciplina, etc)
q_ids = list(set([a['question_id'] for a in ans_data]))
q_data, _ = run_query("questions", select="id, disciplina", filters={"id": q_ids})

# Merge dos dados no Pandas
df_ans = pd.DataFrame(ans_data)
df_q = pd.DataFrame(q_data)
df = pd.merge(df_ans, df_q, left_on="question_id", right_on="id")

# --- Cálculo de Métricas ---
total_respondidas = len(df)
total_acertos = df['is_correct'].sum()
total_erros = total_respondidas - total_acertos
taxa_acerto = (total_acertos / total_respondidas) * 100

# --- Linha de Métricas ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de Questões", total_respondidas)
c2.metric("Acertos", total_acertos)
c3.metric("Erros", total_erros)
c4.metric("Aproveitamento", f"{taxa_acerto:.1f}%")

st.markdown("---")

# --- Gráficos ---
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.subheader("Visão Geral")
    # Gráfico de Rosca (Donut)
    fig_donut = go.Figure(data=[go.Pie(
        labels=['Acertos', 'Erros'], 
        values=[total_acertos, total_erros], 
        hole=.5,
        marker_colors=['#28A745', '#DC3545']
    )])
    fig_donut.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
    st.plotly_chart(fig_donut, use_container_width=True)

with col_graf2:
    st.subheader("Desempenho por Disciplina")
    # Agrupamento por disciplina
    df_disc = df.groupby('disciplina').agg(
        Total=('is_correct', 'count'),
        Acertos=('is_correct', 'sum')
    ).reset_index()
    df_disc['Taxa (%)'] = (df_disc['Acertos'] / df_disc['Total']) * 100
    df_disc = df_disc.sort_values('Taxa (%)', ascending=True)

    # Gráfico de Barras Horizontal
    fig_bar = px.bar(
        df_disc, 
        x='Taxa (%)', 
        y='disciplina', 
        orientation='h',
        text=df_disc['Taxa (%)'].apply(lambda x: f"{x:.1f}%"),
        color='Taxa (%)',
        color_continuous_scale="Blues"
    )
    fig_bar.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300, showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

# --- Tabela Detalhada ---
st.subheader("Histórico Detalhado")
df_table = df[['answered_at', 'disciplina', 'is_correct']].copy()
df_table['answered_at'] = pd.to_datetime(df_table['answered_at']).dt.strftime('%d/%m/%Y %H:%M')
df_table['is_correct'] = df_table['is_correct'].apply(lambda x: "✅ Acerto" if x else "❌ Erro")
df_table.columns = ['Data', 'Disciplina', 'Resultado']

st.dataframe(df_table.sort_values('Data', ascending=False), use_container_width=True, hide_index=True)
