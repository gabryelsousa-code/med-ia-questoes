import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="MedIA - Gemini Pro", 
    page_icon="🏥", 
    layout="wide"
)

# --- ESTADO DA SESSÃO (MEMÓRIA) ---
if 'questoes_geradas' not in st.session_state:
    st.session_state.questoes_geradas = []
if 'questoes_prova' not in st.session_state:
    st.session_state.questoes_prova = []
if 'correcoes' not in st.session_state:
    st.session_state.correcoes = {}

# --- FUNÇÕES ---
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
    st.title("🩺 MedIA (Gemini)")
    api_key = st.text_input("Sua API Key do Google (Começa com AIza...):", type="password")
    
    st.markdown("---")
    modo = st.radio("Escolha o Modo:", ["📝 Gerador de Questões (Criar)", "✅ Corretor de Provas (Resolver)"])
    
    st.markdown("---")
    if st.button("🗑️ Limpar Memória"):
        st.session_state.questoes_geradas = []
        st.session_state.questoes_prova = []
        st.session_state.correcoes = {}
        st.rerun()

# --- MODO 1: GERADOR (CRIAR QUESTÕES) ---
if modo == "📝 Gerador de Questões (Criar)":
    st.header("Gerador de Simulados")
    st.markdown("Crie até 100 questões inéditas baseadas em seus resumos.")
    
    arquivo_gerador = st.file_uploader("Upload do Material de Estudo (PDF)", type="pdf", key="upl_gerador")
    
    col1, col2 = st.columns(2)
    # Slider ajustado para até 100 questões
    qtd_questoes = col1.slider("Quantidade de Questões", 1, 100, 5) 
    dificuldade = col2.selectbox("Dificuldade", ["Internato", "Residência Médica", "R3 / Título de Especialista"])
    
    if arquivo_gerador and api_key:
        if st.button(f"🚀 Gerar {qtd_questoes} Questões"):
            with st.spinner(f"A IA está lendo o PDF e criando {qtd_questoes} questões (isso pode levar 1 ou 2 minutos)..."):
                texto = extrair_texto_pdf(arquivo_gerador)
                client = get_client(api_key)
                
                # Prompt instruindo a usar a busca para validar
                prompt = f"""
                Você é uma banca examinadora de medicina.
                
                TAREFA:
                Crie exatas {qtd_questoes} questões de múltipla escolha baseadas no texto enviado.
                Nível: {dificuldade}.
                
                REGRAS:
                1. Use o texto enviado como base, mas valide o gabarito com a BUSCA DO GOOGLE (Diretrizes 2024/2025).
                2. Priorize fontes brasileiras (SBC, Febrasgo, MS, Estratégia MED).
                
                TEXTO BASE (Resumo):
                "{texto}"
                
                FORMATO JSON OBRIGATÓRIO:
                [
                    {{
                        "enunciado": "...",
                        "alternativas": {{ "A": "...", "B": "...", "C": "...", "D": "..." }},
                        "resposta_correta": "A",
                        "comentario": "Breve explicação citando a fonte..."
                    }}
                ]
                """
                
                try:
                    # Usando gemini-1.5-flash pois ele aguenta textos gigantes (1 milhão de tokens)
                    response = client.models.generate_content(
                        model='gemini-1.5-flash', 
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())], # Ativa a busca nativa
                            response_mime_type='application/json'
                        )
                    )
                    st.session_state.questoes_geradas = json.loads(response.text)
                    st.success("Questões geradas com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao gerar: {e}. Tente gerar em lotes menores (ex: 20 por vez) se der erro de tempo.")

    # Exibir Questões Geradas
    if st.session_state.questoes_geradas:
        st.write(f"Total gerado: {len(st.session_state.questoes_geradas)}")
        for i, q in enumerate(st.session_state.questoes_geradas):
            with st.expander(f"Questão {i+1}: {q.get('enunciado', '')[:60]}...", expanded=False):
                st.markdown(f"**{q['enunciado']}**")
                # Proteção caso o JSON venha incompleto
                alts = q.get('alternativas', {})
                st.info(f"A) {alts.get('A', '')}")
                st.info(f"B) {alts.get('B', '')}")
                st.info(f"C) {alts.get('C', '')}")
                st.info(f"D) {alts.get('D', '')}")
                
                if st.button(f"Ver Gabarito {i+1}", key=f"gab_gen_{i}"):
                    st.success(f"Gabarito: {q.get('resposta_correta', '?')}")
                    st.caption(f"Comentário: {q.get('comentario', '')}")

# --- MODO 2: CORRETOR (RESOLVER PROVA) ---
elif modo == "✅ Corretor de Provas (Resolver)":
    st.header("Corretor de Provas (Leitura Completa)")
    st.markdown("Identifica todas as questões do PDF e corrige com base no Estratégia MED/Diretrizes.")
    
    arquivo_prova = st.file_uploader("Upload da Prova Completa", type="pdf", key="upl_prova")
    
    if arquivo_prova and api_key:
        if not st.session_state.questoes_prova:
            if st.button("🔍 Ler Todas as Questões do Arquivo"):
                with st.spinner("Lendo arquivo inteiro (pode levar alguns minutos se tiver muitas páginas)..."):
                    texto = extrair_texto_pdf(arquivo_prova)
                    client = get_client(api_key)
                    
                    # Prompt ajustado para ler TUDO sem cortar
                    prompt = f"""
                    Aja como um extrator de dados.
                    Analise o TEXTO COMPLETO da prova abaixo.
                    Sua missão é extrair TODAS as questões que encontrar, da primeira à última.
                    
                    TEXTO DA PROVA:
                    "{texto}"
                    
                    SAÍDA (JSON):
                    [
                        {{ "numero": 1, "enunciado": "...", "alternativas": ["A) ...", "B) ..."] }},
                        {{ "numero": 2, "enunciado": "...", "alternativas": ["..."] }}
                    ]
                    """
                    try:
                        # O Gemini 1.5 Flash é capaz de processar até 1 milhão de tokens (aprox 700 mil palavras)
                        response = client.models.generate_content(
                            model='gemini-1.5-flash',
                            contents=prompt,
                            config=types.GenerateContentConfig(response_mime_type='application/json')
                        )
                        novas_questoes = json.loads(response.text)
                        st.session_state.questoes_prova = novas_questoes
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao ler prova: {e}. Se o arquivo for muito grande (>100 págs), tente dividir.")

    # Interface de Resolução
    if st.session_state.questoes_prova:
        total = len(st.session_state.questoes_prova)
        st.info(f"Questões encontradas: {total}")
        
        lista_indices = [f"Questão {q.get('numero', i+1)}" for i, q in enumerate(st.session_state.questoes_prova)]
        escolha_idx = st.selectbox("Navegar:", range(len(lista_indices)), format_func=lambda x: lista_indices[x])
        
        q_atual = st.session_state.questoes_prova[escolha_idx]
        
        st.markdown("---")
        st.subheader(f"Questão {q_atual.get('numero', '?')}")
        st.write(q_atual.get('enunciado', ''))
        st.radio("Alternativas:", q_atual.get('alternativas', []), key=f"rad_{escolha_idx}", index=None)
        
        if st.button("🧠 Corrigir (Estratégia/Diretrizes)", key=f"btn_corr_{escolha_idx}"):
            with st.spinner("A IA está pesquisando no Google e sites médicos..."):
                client = get_client(api_key)
                
                # Prompt de Correção com Busca Ativada
                prompt_correcao = f"""
                Você é um professor corrigindo esta questão médica.
                
                Questão: {q_atual.get('enunciado', '')}
                Alternativas: {q_atual.get('alternativas', [])}
                
                MISSÃO DE PESQUISA (Use a ferramenta Google Search):
                1. Pesquise a resolução desta questão.
                2. Tente encontrar a explicação no site 'estrategiamed.com.br' ou 'blog.estrategiamed.com.br'.
                3. Se não achar, busque em Diretrizes Brasileiras (SBC, AMB, MS).
                
                SAÍDA JSON:
                {{
                    "correta": "Letra/Texto da correta",
                    "analise": [
                        {{"alt": "A", "status": "Certa/Errada", "motivo": "Explicação..."}},
                        {{"alt": "B", "status": "Certa/Errada", "motivo": "Explicação..."}}
                    ],
                    "fontes": "Links ou nomes das diretrizes encontradas"
                }}
                """
                try:
                    resp = client.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=prompt_correcao,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())], # Busca ativada
                            response_mime_type='application/json'
                        )
                    )
                    st.session_state.correcoes[escolha_idx] = json.loads(resp.text)
                except Exception as e:
                    st.error(f"Erro: {e}")

        # Mostra correção
        if escolha_idx in st.session_state.correcoes:
            dados = st.session_state.correcoes[escolha_idx]
            st.success(f"Gabarito: {dados.get('correta', '?')}")
            
            if dados.get('fontes'):
                st.caption(f"📚 Fontes: {dados['fontes']}")
            
            st.markdown("### Análise")
            for item in dados.get('analise', []):
                icon = "✅" if "certa" in item['status'].lower() or "correta" in item['status'].lower() else "❌"
                st.markdown(f"**{icon} {item.get('alt', '')} ({item['status']})**: {item['motivo']}")

elif not api_key:
    st.warning("Insira a API Key do Google (AIza...) na barra lateral.")
