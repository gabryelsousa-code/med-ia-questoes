import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="MedIA - Estudo Baseado em Evidências", page_icon="🩺")

st.title("🩺 MedIA: Gerador de Questões Atualizadas")
st.markdown("""
Faça upload de um PDF (artigo, protocolo, diretriz) e a IA criará uma questão de prova,
**validando com as evidências mais recentes da internet**.
""")

# --- BARRA LATERAL (ONDE FICA A CHAVE) ---
with st.sidebar:
    st.header("🔐 Configuração")
    api_key = st.text_input("Cole sua API Key do Google aqui:", type="password")
    st.caption("Obtenha sua chave gratuita em [aistudio.google.com](https://aistudio.google.com)")
    st.warning("Sua chave não é salva. Ela é usada apenas nesta sessão.")

# --- FUNÇÕES ---
def extrair_texto_pdf(arquivo):
    leitor = PdfReader(arquivo)
    texto = ""
    for pagina in leitor.pages:
        texto += pagina.extract_text() + "\n"
    return texto

def gerar_questao(texto_base, chave):
    if not chave:
        return {"erro": "Chave de API não fornecida."}
        
    client = genai.Client(api_key=chave)
    
    prompt = f'''
    Você é um preceptor de residência médica rigoroso.
    
    CONTEXTO:
    O usuário enviou um texto base (extraído de PDF).
    
    SUA MISSÃO:
    1. Leia o texto do usuário.
    2. USE A FERRAMENTA DE BUSCA (Google Search) para encontrar as diretrizes e protocolos mais recentes (2024/2025/2026) sobre o tema.
    3. Crie uma questão de múltipla escolha difícil (nível prova de título).
    4. No comentário, CONFRONTE o texto do usuário com o que você achou na internet.
    
    TEXTO DO USUÁRIO:
    "{texto_base}"
    '''

    try:
        # Usando o alias que sabemos que funciona
        response = client.models.generate_content(
            model='gemini-flash-latest', 
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type='application/json',
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "tema_identificado": {"type": "STRING"},
                        "enunciado": {"type": "STRING"},
                        "alternativas": {
                            "type": "OBJECT",
                            "properties": {
                                "A": {"type": "STRING"},
                                "B": {"type": "STRING"},
                                "C": {"type": "STRING"},
                                "D": {"type": "STRING"}
                            }
                        },
                        "resposta_correta": {"type": "STRING"},
                        "comentario_baseado_em_evidencias": {"type": "STRING"},
                        "fontes_externas_encontradas": {"type": "STRING"}
                    }
                }
            )
        )
        return json.loads(response.text)
    except Exception as e:
        return {"erro": str(e)}

# --- INTERFACE PRINCIPAL ---
uploaded_file = st.file_uploader("Arraste seu PDF aqui", type="pdf")

if uploaded_file:
    if not api_key:
        st.error("⚠️ Por favor, cole sua API Key na barra lateral esquerda para começar.")
    else:
        if st.button("Gerar Questão Baseada em Evidência"):
            with st.spinner('Lendo PDF e pesquisando protocolos atualizados na web...'):
                texto = extrair_texto_pdf(uploaded_file)
                resultado = gerar_questao(texto, api_key)
                
                if "erro" in resultado:
                    st.error(f"Ocorreu um erro: {resultado['erro']}")
                else:
                    st.success(f"Tema: {resultado['tema_identificado']}")
                    st.subheader("📝 Questão")
                    st.write(resultado['enunciado'])
                    
                    opts = resultado['alternativas']
                    st.info(f"A) {opts['A']}")
                    st.info(f"B) {opts['B']}")
                    st.info(f"C) {opts['C']}")
                    st.info(f"D) {opts['D']}")
                    
                    with st.expander("Ver Gabarito e Comentários"):
                        st.markdown(f"**Resposta Correta:** {resultado['resposta_correta']}")
                        st.markdown(f"### 💡 Análise Baseada em Evidências")
                        st.write(resultado['comentario_baseado_em_evidencias'])
                        if resultado.get('fontes_externas_encontradas'):
                            st.caption(f"Fontes: {resultado['fontes_externas_encontradas']}")
