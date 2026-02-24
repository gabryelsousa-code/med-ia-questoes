import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="MedIA - Estratégia de Estudos", 
    page_icon="🦉", 
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
                
                # Prompt atualizado para buscar fontes confiáveis também na geração
                prompt = f"""
                Você é um examinador de banca de residência médica.
                
                CONTEXTO:
                O usuário enviou um texto base.
                
                SUA MISSÃO:
                1. Crie {qtd_questoes} questões de múltipla escolha.
                2. Nível de Dificuldade: {dificuldade}.
                3. USE A BUSCA DO GOOGLE para garantir que o gabarito esteja de acordo com as diretrizes mais recentes (2024/2025).
                4. Priorize citar fontes brasileiras (SBC, SBP, FEBRASGO, Ministério da Saúde) ou grandes portais como Estratégia MED e PEBMED.
                
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
    st.header("Corretor de Provas com IA (Foco Estratégia MED)")
    st.markdown("Envie uma prova (PDF). A IA vai identificar as questões e corrigir cada alternativa usando a internet, **priorizando o Estratégia MED e Diretrizes Oficiais**.")
    
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
                        st.error(f"Erro ao ler prova: {e}")

    # Se já tiver questões extraídas, mostra a interface de resolução
    if st.session_state.questoes_prova:
        opcoes = [f"Questão {q['numero']}" for q in st.session_state.questoes_prova]
        escolha_idx = st.selectbox("Selecione a questão para corrigir:", range(len(opcoes)), format_func=lambda x: opcoes[x])
        
        q_atual = st.session_state.questoes_prova[escolha_idx]
        
        st.markdown("---")
        st.subheader(f"Questão {q_atual['numero']}")
        st.write(q_atual['enunciado'])
        
        # Simular alternativas
        st.radio("Sua resposta:", q_atual['alternativas'], key=f"radio_{escolha_idx}", index=None)
        
        if st.button("🧠 Corrigir com Estratégia/Evidência", key=f"btn_corr_{escolha_idx}"):
            with st.spinner("Consultando Blog Estratégia MED, PEBMED e Diretrizes..."):
                client = get_client(api_key)
                
                # --- PROMPT ATUALIZADO COM SUA SOLICITAÇÃO ---
                prompt_correcao = f"""
                Você é um professor especialista corrigindo uma prova de residência médica.
                
                QUESTÃO A SER CORRIGIDA:
                Enunciado: {q_atual['enunciado']}
                Alternativas: {q_atual['alternativas']}
                
                SUA MISSÃO DE PESQUISA (GOOGLE SEARCH):
                1. Pesquise a resolução desta questão ou o tema clínico dela.
                2. PRIORIDADE MÁXIMA: Busque por resoluções ou artigos nos sites "estrategiamed.com.br" ou "blog.estrategiamed.com.br".
                3. SEGUNDA OPÇÃO: Busque em "pebmed.com.br" ou Diretrizes de Sociedades Brasileiras (SBC, SBP, FEBRASGO, CBMI).
                4. TERCEIRA OPÇÃO: UpToDate ou MSD Manuals.
                
                SAÍDA OBRIGATÓRIA (JSON):
                {{
                    "correta": "Texto da alternativa correta",
                    "analise": [
                        {{"alt": "A", "status": "Correta/Incorreta", "motivo": "Explicação detalhada..."}},
                        {{"alt": "B", "status": "Correta/Incorreta", "motivo": "Explicação detalhada..."}},
                        ... (faça para todas)
                    ],
                    "fontes": "Liste os links encontrados (ex: 'Blog Estratégia MED: Manejo da SEPSE...')"
                }}
                """
                
                try:
                    resp = client.models.generate_content(
                        model='gemini-flash-latest',
                        contents=prompt_correcao,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())],
                            response_mime_type='application/json'
                        )
                    )
                    st.session_state.correcoes[escolha_idx] = json.loads(resp.text)
                except Exception as e:
                    st.error(f"Erro na correção: {e}")

        # Mostrar Correção
        if escolha_idx in st.session_state.correcoes:
            dados = st.session_state.correcoes[escolha_idx]
            
            # Caixa de destaque para a resposta correta
            st.success(f"**Gabarito Oficial:** {dados['correta']}")
            
            if 'fontes' in dados:
                st.info(f"📚 **Fontes Consultadas:** {dados['fontes']}")
            
            st.markdown("### 📝 Comentários por Alternativa")
            for item in dados['analise']:
                icone = "✅" if "correta" in item['status'].lower() else "❌"
                # Formatação visual para facilitar a leitura
                st.markdown(f"""
                **{icone} Alternativa {item.get('alt', '')} ({item['status']})** {item['motivo']}
                """)
                st.divider()

elif not api_key:
    st.warning("⚠️ Insira sua API Key na barra lateral para começar.")
