import streamlit as st
from supabase import create_client, Client
import json
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="MedResidency - Banco de Questões",
    page_icon="🏥",
    layout="wide"
)

# --- ESTADO DA SESSÃO ---
if 'supabase' not in st.session_state: st.session_state.supabase = None
if 'indice_questao' not in st.session_state: st.session_state.indice_questao = 0
if 'questoes_carregadas' not in st.session_state: st.session_state.questoes_carregadas = []
if 'resposta_mostrada' not in st.session_state: st.session_state.resposta_mostrada = False

# --- FUNÇÕES ---
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except:
        return None

def resetar_navegacao():
    st.session_state.indice_questao = 0
    st.session_state.resposta_mostrada = False

def ordenar_alternativas(alternativas):
    """
    Função para garantir que Certo venha antes de Errado,
    e que A, B, C, D fiquem em ordem alfabética.
    """
    chaves = list(alternativas.keys())
    
    # Verifica se é questão de Certo/Errado (Keys: C e E)
    # Usamos upper() para garantir
    chaves_upper = [k.upper() for k in chaves]
    
    if set(chaves_upper) == {'C', 'E'}:
        # Retorna na ordem Certo depois Errado
        return sorted(chaves, key=lambda x: 0 if x.upper() == 'C' else 1)
    
    # Se for V ou F
    if set(chaves_upper) == {'V', 'F'}:
         return sorted(chaves, key=lambda x: 0 if x.upper() == 'V' else 1)

    # Padrão: Ordem alfabética (A, B, C, D...)
    return sorted(chaves)

# --- CONEXÃO AUTOMÁTICA ---
if not st.session_state.supabase:
    st.session_state.supabase = init_supabase()

# --- MENU LATERAL ---
with st.sidebar:
    st.title("🏥 MedResidency")
    st.caption("Plataforma de Treinamento")
    
    if st.session_state.supabase:
        st.success("✅ Banco Conectado")
    else:
        st.error("❌ Banco Desconectado")
        st.warning("Configure 'st.secrets' no painel.")

    st.markdown("---")
    pagina = st.radio("Menu", ["📝 Resolver Questões", "📤 Importar JSON"])

# ==============================================================================
# PÁGINA 1: IMPORTADOR
# ==============================================================================
if pagina == "📤 Importar JSON":
    st.header("Importador de Questões")
    st.info("Suporta Múltipla Escolha e Certo/Errado.")
    
    arquivo_upload = st.file_uploader("Arquivo .json", type="json")
    
    if arquivo_upload and st.session_state.supabase:
        if st.button("💾 Salvar no Banco de Dados"):
            try:
                dados = json.load(arquivo_upload)
                
                if isinstance(dados, list):
                    progresso = st.progress(0)
                    status = st.empty()
                    status.text("Enviando para o Supabase...")
                    
                    st.session_state.supabase.table("banco_questoes").insert(dados).execute()
                    
                    progresso.progress(100)
                    status.text("Concluído!")
                    st.success(f"Sucesso! {len(dados)} questões importadas.")
                    st.balloons()
                else:
                    st.error("O arquivo JSON deve conter uma lista [ ].")
            except Exception as e:
                st.error(f"Erro na importação: {e}")

# ==============================================================================
# PÁGINA 2: SIMULADOR
# ==============================================================================
elif pagina == "📝 Resolver Questões":
    st.header("Simulador de Prova")
    
    if not st.session_state.supabase:
        st.warning("Banco de dados desconectado.")
        st.stop()

    # --- FILTROS ---
    col1, col2 = st.columns(2)
    
    if 'lista_disciplinas' not in st.session_state:
        try:
            res = st.session_state.supabase.table("banco_questoes").select("disciplina").execute()
            lista = sorted(list(set([x['disciplina'] for x in res.data if x['disciplina']])))
            lista.insert(0, "Todas")
            st.session_state.lista_disciplinas = lista
        except:
            st.session_state.lista_disciplinas = ["Todas"]

    filtro_disciplina = col1.selectbox("Disciplina:", st.session_state.lista_disciplinas, on_change=resetar_navegacao)
    
    if st.button("Carregar Questões"):
        try:
            query = st.session_state.supabase.table("banco_questoes").select("*")
            if filtro_disciplina != "Todas":
                query = query.eq("disciplina", filtro_disciplina)
            
            # Limite de 50
            res = query.limit(50).execute()
            
            if res.data:
                st.session_state.questoes_carregadas = res.data
                resetar_navegacao()
                st.rerun()
            else:
                st.warning("Nenhuma questão encontrada.")
        except Exception as e:
            st.error(f"Erro ao buscar: {e}")

    st.markdown("---")

    # --- INTERFACE DA QUESTÃO ---
    if st.session_state.questoes_carregadas:
        qs = st.session_state.questoes_carregadas
        idx = st.session_state.indice_questao
        
        if idx >= len(qs): idx = 0
        q_atual = qs[idx]
        
        # Navegação
        c1, c2, c3 = st.columns([1, 4, 1])
        if c1.button("⬅️ Anterior") and idx > 0:
            st.session_state.indice_questao -= 1
            st.session_state.resposta_mostrada = False
            st.rerun()
            
        c2.markdown(f"<center><b>Questão {idx+1} de {len(qs)}</b><br><small>{q_atual.get('disciplina')} | {q_atual.get('assunto')}</small></center>", unsafe_allow_html=True)
        
        if c3.button("Próxima ➡️") and idx < len(qs)-1:
            st.session_state.indice_questao += 1
            st.session_state.resposta_mostrada = False
            st.rerun()

        # Enunciado
        st.markdown(f"#### {q_atual['enunciado']}")
        
        # --- ALTERNATIVAS INTELIGENTES ---
        alternativas = q_atual.get('alternativas', {})
        
        # Usa a função para ordenar (C antes de E, A antes de B)
        chaves_ordenadas = ordenar_alternativas(alternativas)
        
        # Formata para exibição
        opcoes_formatadas = [f"{k}) {alternativas[k]}" for k in chaves_ordenadas]
        
        escolha = st.radio("Sua resposta:", opcoes_formatadas, index=None, key=f"radio_{q_atual['id']}")
        
        if st.button("✅ Confirmar Resposta"):
            if escolha:
                st.session_state.resposta_mostrada = True
            else:
                st.warning("Selecione uma opção.")

        # --- FEEDBACK ---
        if st.session_state.resposta_mostrada and escolha:
            letra_usuario = escolha.split(")")[0] # Pega "C" ou "E" ou "A"...
            gabarito_oficial = q_atual.get('gabarito', '').strip().upper()
            
            st.divider()
            
            if letra_usuario.upper() == gabarito_oficial:
                st.success(f"**CORRETO!** 🎉")
            else:
                st.error(f"**INCORRETO.** Você marcou {letra_usuario}, mas a correta é **{gabarito_oficial}**.")
            
            st.info(f"💡 **Comentário:**\n\n{q_atual.get('comentario', 'Sem comentário.')}")

    elif st.session_state.get('questoes_carregadas') == []:
        st.info("Clique em 'Carregar Questões' para começar.")
