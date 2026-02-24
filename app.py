import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="MedIA - Plataforma Completa", 
    page_icon="🏥", 
    layout="wide"
)

# --- ESTADO DA SESSÃO ---
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
    st.title("🩺 MedIA Pro")
    api_key = st.text_input("Sua API Key do Google:", type="password")
    
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
    # AQUI MUDAMOS O LIMITE PARA 100
    qtd_questoes = col1.slider("Quantidade de Questões", 1, 100, 5) 
    dificuldade = col2.selectbox("Dificuldade", ["Internato", "Residência Médica", "R3 / Título de Especialista"])
    
    if arquivo_gerador and api_key:
        if st.button(f"🚀 Gerar {qtd_questoes} Questões"):
            with st.spinner(f"Criando {qtd_questoes} questões (isso pode demorar um pouco)..."):
                texto = extrair_texto_pdf(arquivo_gerador)
                client = get_client(api_key)
                
                # Prompt otimizado para grandes volumes
                prompt = f"""
                Você é uma banca examinadora de medicina.
                
                TAREFA:
                Crie exatas {qtd_questoes} questões de múltipla escolha baseadas no texto enviado.
                Nível: {dificuldade}.
                
                REGRAS:
                1. Use o texto enviado como base, mas valide o gabarito com a BUSCA DO GOOGLE (Diretrizes 2024/2025).
                2. Priorize fontes brasileiras (SBC, Febrasgo, MS).
                
                TEXTO BASE (Resumo):
                "{texto}"  # REMOVIDO O LIMITE DE CARACTERES AQUI
                
                FORMATO JSON OBRIGATÓRIO:
                [
                    {{
                        "enunciado": "...",
                        "alternativas": {{ "A": "...", "B": "...", "C": "...", "D": "..." }},
                        "resposta_correta": "A",
                        "comentario": "Breve explicação..."
                    }}
                ]
                """
                
                try:
                    # Usando gemini-1.5-flash pois ele aguenta textos maiores (1 milhão de tokens)
                    response = client.models.generate_content(
                        model='gemini-1.5-flash', 
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())],
                            response_mime_type='application/json'
                        )
                    )
                    st.session_state.questoes_geradas = json.loads(response.text)
                    st.success("Questões geradas com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao gerar: {e}. Tente gerar em lotes menores (ex: 20 por vez) se der erro de tempo.")

    # Exibir
    if st.session_state.questoes_geradas:
        st.write(f"Total gerado: {len(st.session_state.questoes_geradas)}")
        for i, q in enumerate(st.session_state.questoes_geradas):
            with st.expander(f"Questão {i+1}: {q.get('enunciado', '')[:60]}...", expanded=False):
                st.markdown(f"**{q['enunciado']}**")
                st.info(f"A) {q['alternativas']['A']}")
                st.info(f"B) {q['alternativas']['B']}")
                st.info(f"C) {q['alternativas']['C']}")
                st.info(f"D) {q['alternativas']['D']}")
                if st.button(f"Ver Gabarito {i+1}", key=f"gab_gen_{i}"):
                    st.success(f"Gabarito: {q['resposta_correta']}")
                    st.caption(f"Comentário: {q['comentario']}")

# --- MODO 2: CORRETOR (RESOLVER PROVA) ---
elif modo == "✅ Corretor de Provas (Resolver)":
    st.header("Corretor de Provas (Leitura Completa)")
    st.markdown("Identifica todas as questões do PDF e corrige com base no Estratégia MED/Diretrizes.")
    
    arquivo_prova = st.file_uploader("Upload da Prova Completa", type="pdf", key="upl_prova")
    
    if arquivo_prova and api_key:
        if not st.session_state.questoes_prova:
            if st.button("🔍 Ler Todas as Questões do Arquivo"):
                with st.spinner("Lendo arquivo inteiro (pode levar 1-2 minutos para 100 questões)..."):
                    texto = extrair_texto_pdf(arquivo_prova)
                    client = get_client(api_key)
                    
                    # Prompt ajustado para ler TUDO sem cortar
                    prompt = f"""
                    Aja como um extrator de dados.
                    Analise o TEXTO COMPLETO da prova abaixo.
                    Sua missão é extrair TODAS as questões que encontrar, da primeira à última.
                    
                    TEXTO DA PROVA:
                    "{texto}"  # LIMITE REMOVIDO: LÊ O ARQUIVO TODO
                    
                    SAÍDA (JSON):
                    [
                        {{ "numero": 1, "enunciado": "...", "alternativas": ["A) ...", "B) ..."] }},
                        {{ "numero": 2, "enunciado": "...", "alternativas": ["..."] }}
                        ...
                    ]
                    """
                    try:
                        # Gemini 1.5 Flash tem contexto de 1 milhão de tokens, aguenta livros inteiros
                        response = client.models.generate_content(
                            model='gemini-1.5-flash',
                            contents=prompt,
                            config=types.GenerateContentConfig(response_mime_type='application/json')
                        )
                        novas_questoes = json.loads(response.text)
                        st.session_state.questoes_prova = novas_questoes
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao ler prova: {e}. O arquivo pode ser grande demais para uma única resposta. Tente dividir o PDF.")

    # Interface de Resolução
    if st.session_state.questoes_prova:
        total = len(st.session_state.questoes_prova)
        st.info(f"Questões encontradas: {total}")
        
        lista_indices = [f"Questão {q['numero']}" for q in st.session_state.questoes_prova]
        escolha_idx = st.selectbox("Navegar:", range(len(lista_indices)), format_func=lambda x: lista_indices[x])
        
        q_atual = st.session_state.questoes_prova[escolha_idx]
        
        st.markdown("---")
        st.subheader(f"Questão {q_atual['numero']}")
        st.write(q_atual['enunciado'])
        st.radio("Alternativas:", q_atual['alternativas'], key=f"rad_{escolha_idx}", index=None)
        
        if st.button("🧠 Corrigir (Estratégia/Diretrizes)", key=f"btn_corr_{escolha_idx}"):
            with st.spinner("Pesquisando resolução..."):
                client = get_client(api_key)
                prompt_correcao = f"""
                Corrija esta questão médica.
                Questão: {q_atual['enunciado']}
                Alternativas: {q_atual['alternativas']}
                
                PESQUISA:
                1. Prioridade: Portal/Blog Estratégia MED.
                2. Secundário: Diretrizes Brasileiras (SBC, AMB, MS).
                
                SAÍDA JSON:
                {{
                    "correta": "Letra/Texto",
                    "analise": [
                        {{"alt": "A", "status": "...", "motivo": "..."}}
                    ],
                    "fontes": "Links"
                }}
                """
                try:
                    resp = client.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=prompt_correcao,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())],
                            response_mime_type='application/json'
                        )
                    )
                    st.session_state.correcoes[escolha_idx] = json.loads(resp.text)
                except Exception as e:
                    st.error(f"Erro: {e}")

        # Mostra correção
        if escolha_idx in st.session_state.correcoes:
            dados = st.session_state.correcoes[escolha_idx]
            st.success(f"Gabarito: {dados['correta']}")
            st.write(dados.get('fontes', ''))
            for item in dados['analise']:
                icon = "✅" if "correta" in item['status'].lower() else "❌"
                st.write(f"{icon} {item.get('alt', '')}: {item['motivo']}")

elif not api_key:
    st.warning("Insira a API Key.")
