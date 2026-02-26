# --- file: pages/99_Painel_Admin.py
import streamlit as st
import json
from services.auth import require_admin
from services.database import get_supabase

require_admin()
st.title("⚙️ Painel Administrativo")

tab_import, tab_stats = st.tabs(["Importar JSON", "Analytics"])

with tab_import:
    st.write("Importar questões em lote. O JSON deve ser uma lista de objetos.")
    uploaded_file = st.file_uploader("Arquivo JSON", type="json")
    
    if uploaded_file and st.button("Processar Importação"):
        try:
            data = json.load(uploaded_file)
            client = get_supabase()
            count = 0
            
            # Barra de progresso
            my_bar = st.progress(0)
            
            for i, item in enumerate(data):
                # Validação básica
                if 'enunciado' not in item or 'gabarito' not in item:
                    continue
                
                # Check duplicata (via id_original)
                existing = client.table("questions").select("id").eq("id_original", str(item.get('id', ''))).execute()
                
                payload = {
                    "id_original": str(item.get('id', '')),
                    "disciplina": item.get('disciplina'),
                    "assunto": item.get('assunto'),
                    "enunciado": item.get('enunciado'),
                    "alternativas": item.get('alternativas'),
                    "gabarito": item.get('gabarito'),
                    "comentario_estruturado": item.get('comentario_estruturado')
                }
                
                if existing.data:
                    # Update
                    client.table("questions").update(payload).eq("id", existing.data[0]['id']).execute()
                else:
                    # Insert
                    client.table("questions").insert(payload).execute()
                
                count += 1
                my_bar.progress((i + 1) / len(data))
                
            st.success(f"{count} questões processadas com sucesso!")
            
        except Exception as e:
            st.error(f"Erro no processamento: {e}")

with tab_stats:
    st.write("Métricas de uso do sistema (Implementar queries de count)")
