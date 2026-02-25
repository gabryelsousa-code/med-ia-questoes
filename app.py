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
def init_supabase():
    """
    Tenta conectar usando st.secrets (configuração salva na nuvem)
    """
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        return None

def resetar_navegacao():
    st.session_state.indice_questao = 0
    st.session_state.resposta_mostrada = False

# --- CONEXÃO AUTOMÁTICA AO INICIAR ---
if not st.session_state.supabase:
    st.session_state.supabase = init_supabase()

# --- MENU LATERAL ---
with st.sidebar:
    st.title("🏥 MedResidency")
    st.caption("Sistema de Preparação para Residência")
    
    st.markdown("### 🔌 Status da Conexão")
    if st.session_state.supabase:
        st.success("✅ Conectado ao Supabase")
    else:
        st.error("❌ Não conectado")
        st.warning("Configure as 'Secrets' no painel do Streamlit Cloud.")

    st.markdown("---")
    pagina = st.radio("Navegação", ["📝 Resolver Questões", "📤 Importar JSON"])

# --- PÁGINA 1: IMPORTADOR DE QUESTÕES ---
if pagina == "📤 Importar JSON":
    st.header("Importador de Questões em Lote")
    st.info("O arquivo JSON deve conter uma lista de objetos com: disciplina, assunto, enunciado, alternativas (objeto), gabarito e comentario.")
    
    arquivo_upload = st.file_uploader("Selecione o arquivo .json", type="json")
    
    if arquivo_upload:
        if not st.session_state.supabase:
            st.error("Erro de conexão com o banco. Verifique as Secrets.")
        else:
            if st.button("Processar e Salvar no Banco"):
                try:
                    dados = json.load(arquivo_upload)
                    
                    if isinstance(dados, list):
                        progresso = st.progress(0)
                        status_text = st.empty()
                        
                        try:
                            # Inserção
                            status_text.text("Enviando dados para o Supabase...")
                            st.session_state.supabase.table("banco_questoes").insert(dados).execute()
                            
                            progresso.progress(100)
                            status_text.text("Concluído!")
                            st.success(f"Sucesso! {len(dados)} questões foram importadas.")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Erro ao inserir no Supabase: {e}")
                    else:
                        st.error("O JSON deve ser uma lista [...] de questões.")
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo JSON: {e}")

# --- PÁGINA 2: RESOLVER QUESTÕES ---
elif pagina == "📝 Resolver Questões":
    st.header("Simulador de Prova")
    
    if not st.session_state.supabase:
        st.warning("Banco de dados desconectado. Configure as chaves no Streamlit Secrets.")
        st.stop()

    # --- FILTROS ---
    col1, col2 = st.columns(2)
    
    # Busca disciplinas disponíveis (com cache simples para não pesar)
    if 'lista_disciplinas' not in st.session_state:
        try:
            res_disciplinas = st.session_state.supabase.table("banco_questoes").select("disciplina").execute()
            if res_disciplinas.data:
                # Cria lista única e ordenada
                lista = sorted(list(set([x['disciplina'] for x in res_disciplinas.data if x['disciplina']])))
                lista.insert(0, "Todas")
                st.session_state.lista_disciplinas = lista
            else:
                st.session_state.lista_disciplinas = ["Todas"]
        except:
            st.session_state.lista_disciplinas = ["Todas"]

    disciplina_filtro = col1.selectbox("Filtrar por Disciplina:", st.session_state.lista_disciplinas, on_change=resetar_navegacao)
    
    # Botão para carregar questões
    if st.button("Buscar Questões"):
        try:
            query = st.session_state.supabase.table("banco_questoes").select("*")
            if disciplina_filtro != "Todas":
                query = query.eq("disciplina", disciplina_filtro)
            
            # Limita a 50 questões aleatórias (ou sequenciais)
            resultado = query.limit(50).execute()
            
            if resultado.data:
                st.session_state.questoes_carregadas = resultado.data
                st.session_state.indice_questao = 0
                st.session_state.resposta_mostrada = False
                st.rerun()
            else:
                st.warning("Nenhuma questão encontrada com esses filtros.")
        except Exception as e:
            st.error(f"Erro ao buscar: {e}")

    st.markdown("---")

    # --- ÁREA DE RESOLUÇÃO ---
    if st.session_state.questoes_carregadas:
        questoes = st.session_state.questoes_carregadas
        idx = st.session_state.indice_questao
        
        # Proteção contra índice fora do limite
        if idx >= len(questoes):
            idx = 0
            st.session_state.indice_questao = 0
            
        questao_atual = questoes[idx]
        
        # Barra de Navegação
        col_nav1, col_nav2, col_nav3 = st.columns([1, 4, 1])
        if col_nav1.button("⬅️ Anterior") and idx > 0:
            st.session_state.indice_questao -= 1
            st.session_state.resposta_mostrada = False
            st.rerun()
        
        col_nav2.markdown(f"<center><b>Questão {idx + 1} de {len(questoes)}</b><br><span style='color:gray'>{questao_atual.get('disciplina','')} - {questao_atual.get('assunto','')}</span></center>", unsafe_allow_html=True)
        
        if col_nav3.button("Próxima ➡️") and idx < len(questoes) - 1:
            st.session_state.indice_questao += 1
            st.session_state.resposta_mostrada = False
            st.rerun()

        # Enunciado
        st.markdown(f"### {questao_atual['enunciado']}")
        
        # Alternativas
        alts = questao_atual.get('alternativas', {})
        # Ordena as chaves (A, B, C, D) para garantir a ordem visual
        chaves_ordenadas = sorted(alts.keys())
        opcoes_formatadas = [f"{k}) {alts[k]}" for k in chaves_ordenadas]
        
        escolha = st.radio("Selecione:", options=opcoes_formatadas, index=None, key=f"q_{questao_atual['id']}")
        
        # Botão Confirmar
        if st.button("✅ Confirmar Resposta"):
            if escolha:
                st.session_state.resposta_mostrada = True
            else:
                st.warning("Escolha uma alternativa.")

        # --- FEEDBACK ---
        if st.session_state.resposta_mostrada and escolha:
            letra_escolhida = escolha.split(")")[0] # Pega "A" de "A) Texto..."
            gabarito = questao_atual.get('gabarito', '').strip()
            
            st.divider()
            
            # Compara ignorando maiúsculas/minúsculas
            if letra_escolhida.upper() == gabarito.upper():
                st.success(f"**CORRETO!** 🎉")
            else:
                st.error(f"**INCORRETO.** Você marcou {letra_escolhida}, mas a correta é **{gabarito}**.")
            
            # Área de Comentário
            with st.chat_message("assistant"):
                st.markdown("#### 💡 Comentário do Professor")
                st.write(questao_atual.get('comentario', 'Sem comentário cadastrado.'))

    elif st.session_state.get('questoes_carregadas') == []:
        st.info("Use os filtros acima e clique em 'Buscar Questões' para começar.")
