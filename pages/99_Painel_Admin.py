# --- file: pages/99_Painel_Admin.py ---
import streamlit as st
import json
import pandas as pd
from services.auth import require_auth, logout
from services.database import get_supabase, run_query
from utils.components import inject_custom_css

st.set_page_config(layout="wide", page_title="Admin | MedResidency")
inject_custom_css()
require_auth()

# Proteção extra: Verificar se é admin
if st.session_state.profile.get('role') != 'admin':
    st.error("Acesso restrito. Você não tem permissão de Administrador.")
    st.stop()

with st.sidebar:
    st.markdown(f"**Admin: {st.session_state.profile['full_name']}**")
    st.markdown("---")
    if st.button("⬅️ Voltar ao App", use_container_width=True): st.switch_page("pages/01_Dashboard.py")
    st.markdown("---")
    if st.button("Sair da Conta"): logout()

st.title("⚙️ Painel de Administração")

tab_import, tab_manage = st.tabs(["📤 Importar Banco (JSON)", "📝 Gerenciar Questões"])

with tab_import:
    st.markdown("### Importação em Lote")
    st.info("Faça o upload do JSON gerado pela IA no formato padrão do sistema.")
    
    arquivo = st.file_uploader("Selecione o arquivo JSON", type=['json'])
    if arquivo and st.button("Processar Importação", type="primary"):
        try:
            dados = json.load(arquivo)
            if not isinstance(dados, list):
                st.error("O JSON deve ser uma lista (array) de questões.")
            else:
                client = get_supabase()
                progresso = st.progress(0)
                sucessos = 0
                
                for i, q in enumerate(dados):
                    # Prepara o payload seguro
                    payload = {
                        "id_original": str(q.get("id_original", f"imp_{i}")),
                        "disciplina": q.get("disciplina", "Geral"),
                        "assunto": q.get("assunto", ""),
                        "enunciado": q.get("enunciado", ""),
                        "alternativas": q.get("alternativas", {}),
                        "gabarito": str(q.get("gabarito", "")).upper(),
                        "comentario_estruturado": q.get("comentario_estruturado"),
                        "banca": q.get("banca", ""),
                        "ano": q.get("ano", None)
                    }
                    client.table("questions").insert(payload).execute()
                    sucessos += 1
                    progresso.progress((i + 1) / len(dados))
                
                st.success(f"✅ {sucessos} questões importadas com sucesso!")
        except Exception as e:
            st.error(f"Erro ao importar: {e}")

with tab_manage:
    st.markdown("### Banco de Dados Atual")
    dados_q, count = run_query("questions", select="id, id_original, disciplina, assunto, enunciado", limit=100)
    
    if dados_q:
        df = pd.DataFrame(dados_q)
        st.dataframe(df, use_container_width=True)
        
        id_deletar = st.text_input("Cole o ID (UUID) da questão para deletar:")
        if st.button("Deletar Questão", type="primary") and id_deletar:
            try:
                client = get_supabase()
                client.table("questions").delete().eq("id", id_deletar).execute()
                st.success("Questão deletada!")
                st.rerun()
            except Exception as e:
                st.error("Erro ao deletar.")
