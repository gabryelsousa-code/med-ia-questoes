import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="MedIA - Plataforma de Estudos", 
    page_icon="🩺", 
    layout="wide"
)

# --- ESTADO DA SESSÃO (MEMÓRIA) ---
if 'questoes_geradas' not in st.session_state:
    st.session_state.questoes_geradas = []
if 'questoes_prova' not in st.session_state:
    st.session_state.questoes_prova = []
if 'correcoes' not in st.session_state:
    st.session_state.correcoes = {}

# --- FUNÇÕES AUXILIARES ---
def extrair_texto_pdf(arquivo):
    leitor = PdfReader(arquivo)
    texto = ""
    for pagina in leitor.pages:
        texto += pagina.extract_text() + "\n"
    return texto

def get_client(api_key):
    return genai.Client(api_key=api_key)

# --- MENU LATERAL ---
with st.sidebar:
    st.title("🩺 MedIA")
    api_key = st.text_input("Cole sua API Key do Google:", type="password")
    
    st.markdown("---")
    modo = st.radio("Escolha o Modo:", ["📝 Gerador de Questões", "✅ Corretor de Provas"])
    
    st.markdown("---")
    if st.button("🧹 Limpar Tudo"):
        st.session_state.questoes_geradas = []
        st.session_state.questoes_prova = []
        st.session_state.correcoes = {}
        st.rerun()

# --- MODO 1: GERADOR DE QUESTÕES ---
if modo == "📝 Gerador de Questões":
    st.header("Gerador de Questões Baseado em Evidências")
    st.markdown("Envie um PDF (resumo, artigo) e a IA criará questões inéditas validando com a internet.")
    
    arquivo_gerador = st.file_uploader("Upload do PDF para Base", type="pdf", key="upl_gerador")
    
    col1, col2 = st.columns(2)
    qtd_questoes = col1.slider("Quantidade de Questões", 1, 5, 1)
    dificuldade = col2.selectbox("Nível de Dificuldade", ["Internato (Médio)", "Residência Médica (Difícil)", "Prova de Título/R3 (Muito Difícil)"])
    
    if arquivo_gerador and api_key:
        if st.button("🚀 Gerar Questões"):
            with st.spinner("Lendo PDF e pesquisando diretrizes atualizadas..."):
                texto = extrair_texto_pdf(arquivo_gerador)
                client = get_client(api_key)
                
                prompt = f"""
                Você é um examinador de banca de residência médica.
                
                CONTEXTO:
                O usuário enviou um texto base.
                
                SUA MISSÃO:
                1. Crie {qtd_questoes} questões de múltipla escolha.
                2. Nível de Dificuldade: {dificuldade}.
                3. USE A BUSCA DO GOOGLE para garantir que o gabarito esteja de acordo com as diretrizes mais recentes (2024/2025).
                4. Confronte o texto do usuário com a literatura atual no comentário.
                
                TEXTO BASE:
                "{texto[:30000]}"
                
                FORMATO JSON OBRIGATÓRIO (LISTA DE OBJETOS):
                [
                    {{
                        "enunciado": "...",
                        "alternativas": {{ "A": "...", "B": "...", "C": "...", "D": "..." }},
                        "resposta_correta": "A",
                        "comentario": "Explicação citando fontes..."
                    }}
                ]
                """
                
                try:
                    response = client.models.generate_content(
                        model='gemini-flash-latest',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())],
                            response_mime_type='application/json'
                        )
                    )
                    st.session_state.questoes_geradas = json.loads(response.text)
                except Exception as e:
                    st.error(f"Erro: {e}")

    # Exibir Questões Geradas
    if st.session_state.questoes_geradas:
        for i, q in enumerate(st.session_state.questoes_geradas):
            with st.expander(f"Questão {i+1}: {q.get('enunciado', '')[:50]}...", expanded=True):
                st.write(q['enunciado'])
                st.info(f"A) {q['alternativas']['A']}")
                st.info(f"B) {q['alternativas']['B']}")
                st.info(f"C) {q['alternativas']['C']}")
                st.info(f"D) {q['alternativas']['D']}")
                
                if st.button(f"Ver Gabarito Q{i+1}", key=f"gab_{i}"):
                    st.success(f"Correta: {q['resposta_correta']}")
                    st.warning(f"Comentário: {q['comentario']}")

# --- MODO 2: CORRETOR DE PROVAS ---
elif modo == "✅ Corretor de Provas":
    st.header("Corretor de Provas com IA")
    st.markdown("Envie uma prova (PDF). A IA vai identificar as questões e corrigir cada alternativa usando a internet.")
    
    arquivo_prova = st.file_uploader("Upload da Prova", type="pdf", key="upl_prova")
    
    if arquivo_prova and api_key:
        # Botão para extrair questões do PDF
        if not st.session_state.questoes_prova:
            if st.button("🔍 Identificar Questões"):
                with st.spinner("Analisando estrutura da prova..."):
                    texto = extrair_texto_pdf(arquivo_prova)
                    client = get_client(api_key)
                    prompt = f"""
                    Extraia as questões deste texto de prova.
                    Retorne uma lista JSON.
                    Texto: "{texto[:30000]}"
                    Formato: [{{ "numero": 1, "enunciado": "...", "alternativas": ["..."] }}]
                    """
                    try:
                        response = client.models.generate_content(
                            model='gemini-flash-latest',
                            contents=prompt,
                            config=types.GenerateContentConfig(response_mime_type='application/json')
                        )
                        st.session_state.questoes_prova = json.loads(response.text)
                        st.rerun()
                    except Exception as e:
                        st.error(f
