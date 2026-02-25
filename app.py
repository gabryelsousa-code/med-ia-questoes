import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
from duckduckgo_search import DDGS
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="MedIA - GPT Edition", 
    page_icon="🧠", 
    layout="wide"
)

# --- ESTADO DA SESSÃO ---
if 'questoes_geradas' not in st.session_state:
    st.session_state.questoes_geradas = []
if 'questoes_prova' not in st.session_state:
    st.session_state.questoes_prova = []
if 'correcoes' not in st.session_state:
    st.session_state.correcoes = {}

# --- FUNÇÕES DE UTILIDADE ---
def extrair_texto_pdf(arquivo):
    leitor = PdfReader(arquivo)
    texto = ""
    for pagina in leitor.pages:
        texto += pagina.extract_text() + "\n"
    return texto

def pesquisar_na_web(termo_busca):
    """
    Simula a 'navegação' do GPT.
    Busca no DuckDuckGo focando em sites médicos brasileiros.
    """
    ddgs = DDGS()
    # Forçamos a busca em sites confiáveis
    query = f"{termo_busca} (site:estrategiamed.com.br OR site:pebmed.com.br OR site:scielo.br OR site:gov.br/saude)"
    
    resultados = []
    # Pega os 3 primeiros resultados para dar contexto
    try:
        results = ddgs.text(query, max_results=3)
        if results:
            for r in results:
                resultados.append(f"Título: {r['title']}\nResumo: {r['body']}\nLink: {r['href']}")
    except Exception as e:
        return f"Erro na busca: {e}"
    
    return "\n---\n".join(resultados)

# --- MENU LATERAL ---
with st.sidebar:
    st.title("🧠 MedIA (GPT-4o)")
    api_key = st.text_input("Sua API Key da OpenAI (sk-...):", type="password")
    
    st.info("💡 Usando modelo GPT-4o para raciocínio clínico avançado.")
    
    st.markdown("---")
    modo = st.radio("Escolha o Modo:", ["📝 Gerador de Questões", "✅ Corretor de Provas"])
    
    if st.button("🗑️ Limpar Memória"):
        st.session_state.questoes_geradas = []
        st.session_state.questoes_prova = []
        st.session_state.correcoes = {}
        st.rerun()

# --- MODO 1: GERADOR ---
if modo == "📝 Gerador de Questões":
    st.header("Gerador de Simulados (GPT-4o)")
    arquivo_gerador = st.file_uploader("Upload do Resumo (PDF)", type="pdf")
    
    col1, col2 = st.columns(2)
    qtd = col1.slider("Quantidade", 1, 50, 5)
    dif = col2.selectbox("Dificuldade", ["Internato", "Residência", "R3/Título"])
    
    if arquivo_gerador and api_key:
        if st.button("🚀 Gerar Questões"):
            with st.spinner("Lendo PDF e criando questões..."):
                texto = extrair_texto_pdf(arquivo_gerador)
                client = OpenAI(api_key=api_key)
                
                prompt = f"""
                Você é uma banca examinadora.
                Crie {qtd} questões de medicina nível {dif} baseadas no texto abaixo.
                
                IMPORTANTE:
                Retorne APENAS um JSON válido no formato:
                [
                    {{
                        "enunciado": "...",
                        "alternativas": {{ "A": "...", "B": "...", "C": "...", "D": "..." }},
                        "resposta_correta": "A",
                        "comentario": "Explicação breve."
                    }}
                ]
                
                TEXTO BASE:
                {texto[:50000]}
                """
                
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}],
                        response_format={ "type": "json_object" } # Força JSON
                    )
                    conteudo = response.choices[0].message.content
                    # Às vezes o GPT devolve um dict {"questoes": [...]}, tratamos isso:
                    dados = json.loads(conteudo)
                    st.session_state.questoes_geradas = dados if isinstance(dados, list) else dados.get('questoes', []) or list(dados.values())[0]
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

    # Exibir Geradas
    if st.session_state.questoes_geradas:
        for i, q in enumerate(st.session_state.questoes_geradas):
            with st.expander(f"Questão {i+1}: {q.get('enunciado', '')[:60]}..."):
                st.write(q['enunciado'])
                st.info(f"A) {q.get('alternativas', {}).get('A')}")
                st.info(f"B) {q.get('alternativas', {}).get('B')}")
                st.info(f"C) {q.get('alternativas', {}).get('C')}")
                st.info(f"D) {q.get('alternativas', {}).get('D')}")
                if st.button(f"Ver Gabarito {i}", key=f"g{i}"):
                    st.success(f"Gabarito: {q['resposta_correta']}")
                    st.write(q['comentario'])

# --- MODO 2: CORRETOR ---
elif modo == "✅ Corretor de Provas":
    st.header("Corretor de Provas com Pesquisa Web")
    arquivo_prova = st.file_uploader("Upload da Prova (PDF)", type="pdf")
    
    if arquivo_prova and api_key:
        if not st.session_state.questoes_prova:
            if st.button("🔍 Extrair Questões"):
                with st.spinner("Analisando PDF..."):
                    texto = extrair_texto_pdf(arquivo_prova)
                    client = OpenAI(api_key=api_key)
                    
                    prompt = f"""
                    Extraia TODAS as questões deste texto.
                    Retorne JSON: {{ "questoes": [ {{ "numero": 1, "enunciado": "...", "alternativas": ["..."] }} ] }}
                    
                    TEXTO:
                    {texto[:60000]}
                    """
                    try:
                        resp = client.chat.completions.create(
                            model="gpt-4o-mini", # Usa o mini aqui para ser rápido e barato na leitura
                            messages=[{"role": "user", "content": prompt}],
                            response_format={ "type": "json_object" }
                        )
                        dados = json.loads(resp.choices[0].message.content)
                        st.session_state.questoes_prova = dados.get('questoes', [])
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro na extração: {e}")

    if st.session_state.questoes_prova:
        indices = [f"Q{q['numero']}" for q in st.session_state.questoes_prova]
        escolha = st.selectbox("Selecione:", range(len(indices)), format_func=lambda x: indices[x])
        q_atual = st.session_state.questoes_prova[escolha]
        
        st.markdown("---")
        st.subheader(f"Questão {q_atual['numero']}")
        st.write(q_atual['enunciado'])
        st.radio("Alternativas:", q_atual['alternativas'], key=f"r{escolha}", index=None)
        
        if st.button("🧠 Corrigir (Pesquisar Estratégia/Diretrizes)"):
            with st.spinner("Pesquisando na web e analisando..."):
                # 1. Pesquisa primeiro (Python faz isso)
                contexto_web = pesquisar_na_web(f"Medicina questão: {q_atual['enunciado'][:100]}")
                
                # 2. Envia para o GPT com o contexto
                client = OpenAI(api_key=api_key)
                prompt_correcao = f"""
                Corrija esta questão médica.
                
                CONTEXTO ENCONTRADO NA WEB (Use isso como base):
                {contexto_web}
                
                QUESTÃO:
                {q_atual['enunciado']}
                Alternativas: {q_atual['alternativas']}
                
                SAÍDA JSON:
                {{
                    "correta": "Texto da correta",
                    "analise": [
                        {{ "alt": "A", "status": "Certa/Errada", "motivo": "..." }}
                    ],
                    "fontes": "Resumo das fontes usadas"
                }}
                """
                
                try:
                    resp = client.chat.completions.create(
                        model="gpt-4o", # Usa o modelo FORTE para corrigir
                        messages=[{"role": "user", "content": prompt_correcao}],
                        response_format={ "type": "json_object" }
                    )
                    st.session_state.correcoes[escolha] = json.loads(resp.choices[0].message.content)
                except Exception as e:
                    st.error(f"Erro: {e}")

        # Mostrar Correção
        if escolha in st.session_state.correcoes:
            d = st.session_state.correcoes[escolha]
            st.success(f"**Gabarito:** {d['correta']}")
            st.info(f"Fontes: {d.get('fontes', 'ChatGPT Knowledge + Web Search')}")
            
            for item in d.get('analise', []):
                icone = "✅" if "certa" in item['status'].lower() or "correta" in item['status'].lower() else "❌"
                st.write(f"{icone} **{item.get('alt')}**: {item['motivo']}")

elif not api_key:
    st.warning("Insira sua API Key da OpenAI.")
