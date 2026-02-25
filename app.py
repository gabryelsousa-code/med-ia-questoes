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

# --- ESTADO DA SESSÃO (VARIÁVEIS GLOBAIS) ---
if 'supabase' not in st.session_state:
    st.session_state.supabase = None
if 'indice_questao' not in st.session_state:
    st.session_state.indice_questao = 0
if 'questoes_carregadas' not in st.session_state:
    st.session_state.questoes_carregadas = []
if 'resposta_mostrada' not in st.session_state:
    st.session_state.resposta_mostrada = False

# --- FUNÇÕES AUXILIARES ---
def init_supabase(url, key):
    try:
        return create_client(url, key)
    except Exception as e:
        return None

def resetar_navegacao():
    st.session_state.indice_questao = 0
    st.session_state.resposta_mostrada = False

# --- MENU LATERAL ---
with st.sidebar:
    st.title("🏥 MedResidency")
    st.caption("Sistema de Preparação para Residência")
    
    with st.expander("⚙️ Configuração do Banco", expanded=True):
        supa_url = st.text_input("Supabase URL:", type="password")
        supa_key = st.text_input("Supabase Key:", type="password")
        
        if supa_url and supa_key:
            st.session_state.supabase = init_supabase(supa_url, supa_key)
            if st.session_state.supabase:
                st.success("Conectado ao Banco!")
            else:
                st.error("Falha na conexão.")

    st.markdown("---")
    pagina = st.radio("Navegação", ["📝 Resolver Questões", "📤 Importar JSON"])

# --- PÁGINA 1: IMPORTADOR DE QUESTÕES ---
if pagina == "📤 Importar JSON":
    st.header("Importador de Questões em Lote")
    st.info("O arquivo JSON deve conter uma lista de objetos com: disciplina, assunto, enunciado, alternativas (objeto), gabarito e comentario.")
    
    arquivo_upload = st.file_uploader("Selecione o arquivo .json", type="json")
    
    if arquivo_upload and st.session_state.supabase:
        if st.button("Processar e Salvar no Banco"):
            try:
                dados = json.load(arquivo_upload)
                
                # Validação simples
                if isinstance(dados, list):
                    progresso = st.progress(0)
                    total = len(dados)
                    
                    # Inserção em Lote (Batch Insert)
                    try:
                        st.session_state.supabase.table("banco_questoes").insert(dados).execute()
                        progresso.progress(100)
                        st.success(f"Sucesso! {total} questões foram importadas para o banco.")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erro ao inserir no Supabase: {e}")
                else:
                    st.error("O JSON deve ser uma lista [...] de questões.")
            except Exception as e:
                st.error(f"Erro ao ler o arquivo JSON: {e}")
    elif not st.session_state.supabase:
        st.warning("Conecte o Supabase na barra lateral antes de importar.")

# --- PÁGINA 2: RESOLVER QUESTÕES ---
elif pagina == "📝 Resolver Questões":
    st.header("Simulador de Prova")
    
    if not st.session_state.supabase:
        st.warning("Por favor, conecte o banco de dados na barra lateral.")
        st.stop()

    # --- FILTROS ---
    col1, col2 = st.columns(2)
    
    # Busca disciplinas disponíveis no banco para o filtro
    try:
        res_disciplinas = st.session_state.supabase.table("banco_questoes").select("disciplina").execute()
        lista_disciplinas = sorted(list(set([x['disciplina'] for x in res_disciplinas.data]))) if res_disciplinas.data else []
        lista_disciplinas.insert(0, "Todas")
    except:
        lista_disciplinas = ["Todas"]

    disciplina_filtro = col1.selectbox("Filtrar por Disciplina:", lista_disciplinas, on_change=resetar_navegacao)
    
    # Botão para carregar questões
    if st.button("Buscar Questões"):
        query = st.session_state.supabase.table("banco_questoes").select("*")
        if disciplina_filtro != "Todas":
            query = query.eq("disciplina", disciplina_filtro)
        
        # Limita a 50 questões por vez para não pesar
        resultado = query.limit(50).execute()
        
        if resultado.data:
            st.session_state.questoes_carregadas = resultado.data
            st.session_state.indice_questao = 0
            st.session_state.resposta_mostrada = False
            st.rerun()
        else:
            st.warning("Nenhuma questão encontrada com esses filtros.")

    st.markdown("---")

    # --- ÁREA DE RESOLUÇÃO ---
    if st.session_state.questoes_carregadas:
        questoes = st.session_state.questoes_carregadas
        idx = st.session_state.indice_questao
        questao_atual = questoes[idx]
        
        # Barra de Progresso / Navegação
        col_nav1, col_nav2, col_nav3 = st.columns([1, 4, 1])
        if col_nav1.button("⬅️ Anterior") and idx > 0:
            st.session_state.indice_questao -= 1
            st.session_state.resposta_mostrada = False
            st.rerun()
        
        col_nav2.markdown(f"<center><b>Questão {idx + 1} de {len(questoes)}</b><br><span style='color:gray'>{questao_atual['disciplina']} - {questao_atual['assunto']}</span></center>", unsafe_allow_html=True)
        
        if col_nav3.button("Próxima ➡️") and idx < len(questoes) - 1:
            st.session_state.indice_questao += 1
            st.session_state.resposta_mostrada = False
            st.rerun()

        # Enunciado
        st.markdown(f"### {questao_atual['enunciado']}")
        
        # Alternativas
        alts = questao_atual['alternativas'] # Espera um dict {"A": "...", "B": "..."}
        opcoes_formatadas = [f"{k}) {v}" for k, v in alts.items()]
        
        # O widget radio retorna a string inteira "A) Texto..."
        escolha = st.radio("Selecione a alternativa:", options=opcoes_formatadas, index=None, key=f"q_{questao_atual['id']}")
        
        # Botão de Confirmar
        if st.button("✅ Confirmar Resposta"):
            if escolha:
                st.session_state.resposta_mostrada = True
            else:
                st.warning("Selecione uma alternativa antes de confirmar.")

        # --- FEEDBACK E COMENTÁRIOS ---
        if st.session_state.resposta_mostrada:
            letra_escolhida = escolha.split(")")[0] # Pega só o "A"
            gabarito = questao_atual['gabarito']
            
            st.divider()
            
            if letra_escolhida == gabarito:
                st.success(f"**PARABÉNS! Você acertou!** (Gabarito: {gabarito})")
            else:
                st.error(f"**Você errou.** Sua escolha: {letra_escolhida} | Gabarito Correto: **{gabarito}**")
            
            # Mostra o Comentário
            st.info(f"💡 **Comentário do Professor:**\n\n{questao_atual['comentario']}")

    else:
        st.info("Use os filtros acima e clique em 'Buscar Questões' para começar.")
