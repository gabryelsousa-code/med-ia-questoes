# --- file: pages/03_Simulados.py
import streamlit as st
from services.auth import require_auth
from services.database import get_supabase, run_query

require_auth()
st.title("📂 Meus Simulados")

tab_list, tab_create = st.tabs(["Meus Simulados", "Criar Novo"])

with tab_list:
    exams, _ = run_query("exams", filters={"user_id": st.session_state.user.id}, order=("created_at", "desc"))
    if not exams:
        st.info("Nenhum simulado criado.")
    else:
        for ex in exams:
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"**{ex['title']}** ({ex['mode']})")
                if c2.button("▶️ Abrir", key=ex['id']):
                    # Cria uma nova tentativa (Attempt)
                    client = get_supabase()
                    att = client.table("attempts").insert({
                        "user_id": st.session_state.user.id,
                        "exam_id": ex['id']
                    }).execute()
                    
                    st.session_state.active_attempt_id = att.data[0]['id']
                    st.switch_page("pages/04_Resolver.py")

with tab_create:
    st.subheader("Gerador Automático")
    with st.form("create_exam"):
        title = st.text_input("Nome do Simulado", "Simulado Personalizado")
        mode = st.selectbox("Modo", ["treino", "prova"])
        qtd = st.slider("Quantidade de Questões", 5, 50, 10)
        
        # Filtros para o gerador
        d_opts = ["Cardiologia", "Pediatria", "Cirurgia"] # Deveria vir do banco
        subjects = st.multiselect("Disciplinas", d_opts)
        
        if st.form_submit_button("Gerar Simulado"):
            client = get_supabase()
            
            # 1. Busca questões aleatórias (Postgres random é melhor, mas aqui faremos simples)
            # Para produção: usar .rpc() function no postgres para random sample
            q_query = client.table("questions").select("id").eq("ativo", True)
            if subjects: q_query = q_query.in_("disciplina", subjects)
            q_res = q_query.limit(qtd).execute()
            
            if not q_res.data:
                st.error("Sem questões para esses filtros.")
            else:
                # 2. Cria Exam
                exam = client.table("exams").insert({
                    "user_id": st.session_state.user.id,
                    "title": title,
                    "mode": mode,
                    "is_generated": True
                }).execute()
                exam_id = exam.data[0]['id']
                
                # 3. Linka Questões
                items = [{"exam_id": exam_id, "question_id": q['id']} for q in q_res.data]
                client.table("exam_questions").insert(items).execute()
                
                st.success("Simulado criado com sucesso!")
                st.rerun()
