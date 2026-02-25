import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader
from supabase import create_client, Client
import json
import hashlib

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="MedBank - Estratégia AI", page_icon="🦉", layout="wide")

# --- CONEXÃO COM O BANCO DE DADOS (SUPABASE) ---
if 'supabase' not in st.session_state:
    st.session_state.supabase = None

# --- FUNÇÕES ---
def init_supabase(url, key):
    try:
        return create_client(url, key)
    except:
        return None

def extrair_texto_pdf(arquivo):
    leitor = PdfReader(arquivo)
    texto = ""
    for pagina in leitor.pages:
        texto += pagina.extract_text() + "\n"
    return texto

def gerar_hash_questao(enunciado):
    """Cria um ID único para a questão baseado no texto dela"""
    return hashlib.md5(enunciado.encode()).hexdigest()

def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)

# --- MENU LATERAL ---
with st.sidebar:
    st.title("🦉 MedBank AI")
    
    st.markdown("### 🔑 Credenciais")
    with st.expander("Configurar Acessos", expanded=True):
        google_key = st.text_input("Google API Key (AIza...):", type="password")
        supa_url = st.text_input("Supabase URL:", type="password")
        supa_key = st.text_input("Supabase Key:", type="password")
    
    # Tenta conectar se os dados forem inseridos
    if supa_url and supa_key:
        st.session_state.supabase = init_supabase(supa_url, supa_key)
        if st.session_state.supabase:
            st.success("Banco de Dados Conectado!")
        else:
            st.error("Erro ao conectar no Supabase. Verifique URL e Key.")
    
    st.markdown("---")
    modo = st.radio("Navegação:", ["📝 Resolver Questões (Upload)", "⚡ Gerador de Questões", "📚 Banco de Questões Salvas"])

# --- MODO 1: RESOLVER QUESTÕES (UPLOAD PDF) ---
if modo == "📝 Resolver Questões (Upload)":
    st.header("Upload de Lista de Questões")
    st.caption("Envie um PDF. A IA vai ler, você responde, e ela corrige (salvando a correção no banco).")
    
    arquivo = st.file_uploader("PDF da Prova/Lista", type="pdf")
    
    if arquivo and google_key:
        if 'questoes_extraidas' not in st.session_state:
            if st.button("🔍 Extrair Questões do PDF"):
                with st.spinner("Lendo PDF e estruturando questões..."):
                    texto = extrair_texto_pdf(arquivo)
                    client = get_gemini_client(google_key)
                    
                    # Prompt para extrair a estrutura
                    prompt = f"""
                    Extraia todas as questões deste texto.
                    SAÍDA JSON OBRIGATÓRIA:
                    [
                        {{ "enunciado": "Texto completo da pergunta...", "alternativas": ["A) ...", "B) ..."] }}
                    ]
                    TEXTO: {texto[:100000]}
                    """
                    try:
                        # CORREÇÃO AQUI: Usando o modelo que funciona na sua conta
                        resp = client.models.generate_content(
                            model='gemini-flash-latest',
                            contents=prompt,
                            config=types.GenerateContentConfig(response_mime_type='application/json')
                        )
                        st.session_state.questoes_extraidas = json.loads(resp.text)
