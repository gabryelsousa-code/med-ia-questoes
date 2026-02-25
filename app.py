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
# Vamos pegar as chaves dos "Segredos" do Streamlit ou input lateral
# Para produção, use st.secrets. Para teste, usamos input.
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
    return "\n".join([p.extract_text() for p in leitor.pages])

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
        google_key = st.text_input("Google API Key:", type="password")
        supa_url = st.text_input("Supabase URL:", type="password")
        supa_key = st.text_input("Supabase Key:", type="password")
    
    if supa_url and supa_key:
        st.session_state.supabase = init_supabase(supa_url, supa_key)
        st.success("Banco de Dados Conectado!")
    
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
                    TEXTO: {texto}
                    """
                    try:
                        resp = client.models.generate_content(
                            model='gemini-1.5-flash',
                            contents=prompt,
                            config=types.GenerateContentConfig(response_mime_type='application/json')
                        )
                        st.session_state.questoes_extraidas = json.loads(resp.text)
                        st.session_state.nome_arquivo_atual = arquivo.name
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao ler: {e}")

    # Interface de Resolução
    if 'questoes_extraidas' in st.session_state:
        qs = st.session_state.questoes_extraidas
        indice = st.selectbox("Navegar:", range(len(qs)), format_func=lambda x: f"Questão {x+1}")
        
        q_atual = qs[indice]
        hash_id = gerar_hash_questao(q_atual['enunciado'])
        
        st.markdown("---")
        st.markdown(f"### Questão {indice + 1}")
        st.write(q_atual['enunciado'])
        
        # Seleção do usuário
        resposta_user = st.radio("Alternativas:", q_atual['alternativas'], key=hash_id)
        
        col1, col2 = st.columns([1, 4])
        
        # BOTÃO DE CORREÇÃO
        if col1.button("Responder e Corrigir"):
            # 1. Verifica se já existe no banco (Supabase)
            ja_existe = False
            if st.session_state.supabase:
                data = st.session_state.supabase.table("questoes").select("*").eq("enunciado", q_atual['enunciado']).execute()
                if data.data and data.data[0].get('comentario_ia'):
                    # OPA! Já temos essa resposta salva!
                    st.session_state.correcao_atual = data.data[0]
                    ja_existe = True
            
            # 2. Se não existe, chama a IA
            if not ja_existe:
                with st.spinner("Consultando Estratégia MED, UpToDate e Diretrizes..."):
                    client = get_gemini_client(google_key)
                    prompt_corr = f"""
                    Aja como um professor do Estratégia MED.
                    Corrija esta questão.
                    
                    FONTES OBRIGATÓRIAS (Google Search):
                    1. Portal Estratégia MED.
                    2. Diretrizes Brasileiras (SBC, SBP, FEBRASGO, CFM).
                    3. UpToDate (se disponível resumo público).
                    
                    Questão: {q_atual['enunciado']}
                    Alternativas: {q_atual['alternativas']}
                    
                    SAÍDA JSON:
                    {{
                        "resposta_correta": "Texto da alternativa correta",
                        "status_user": "Se o usuário marcou '{resposta_user}', ele acertou ou errou?",
                        "comentario_geral": "Explicação do tema baseada nas fontes...",
                        "analise_alternativas": [
                            {{"alt": "A", "status": "Correta/Incorreta", "motivo": "..."}},
                            {{"alt": "B", "status": "Correta/Incorreta", "motivo": "..."}}
                        ],
                        "fontes": "Links consultados"
                    }}
                    """
                    resp = client.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=prompt_corr,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())],
                            response_mime_type='application/json'
                        )
                    )
                    correcao_json = json.loads(resp.text)
                    
                    # 3. Salva no Banco para a próxima vez
                    if st.session_state.supabase:
                        novo_registro = {
                            "enunciado": q_atual['enunciado'],
                            "alternativas": q_atual['alternativas'],
                            "resposta_correta": correcao_json['resposta_correta'],
                            "comentario_ia": correcao_json,
                            "fonte_original": st.session_state.get('nome_arquivo_atual', 'Upload')
                        }
                        st.session_state.supabase.table("questoes").insert(novo_registro).execute()
                    
                    st.session_state.correcao_atual = {"comentario_ia": correcao_json}

        # Exibir a Correção (seja do banco ou da IA)
        if 'correcao_atual' in st.session_state:
            dados = st.session_state.correcao_atual['comentario_ia']
            
            st.markdown("---")
            if resposta_user:
                if resposta_user in dados['resposta_correta'] or dados['resposta_correta'] in resposta_user:
                    st.success("PARABÉNS! VOCÊ ACERTOU! 🎉")
                else:
                    st.error(f"VOCÊ ERROU. A correta é: {dados['resposta_correta']}")
            
            st.info(f"**Resumo do Professor:** {dados['comentario_geral']}")
            st.caption(f"📚 Fontes: {dados.get('fontes', 'IA Search')}")
            
            for item in dados['analise_alternativas']:
                icon = "✅" if "correta" in item['status'].lower() else "❌"
                st.markdown(f"**{icon} Alternativa {item.get('alt', '')}**: {item['motivo']}")

# --- MODO 2: GERADOR DE QUESTÕES ---
elif modo == "⚡ Gerador de Questões":
    st.header("Gerador de Simulados")
    pdf_base = st.file_uploader("PDF Base (Livro/Resumo)", type="pdf")
    qtd = st.slider("Quantidade", 1, 20, 5) # Gemini Flash gera melhor em lotes pequenos
    dif = st.selectbox("Dificuldade", ["R1 (Acesso Direto)", "R3 (Especialidade)", "Título"])
    
    if pdf_base and st.button("Gerar e Salvar no Banco"):
        if not st.session_state.supabase:
            st.error("Conecte o Supabase primeiro!")
        else:
            with st.spinner("Gerando questões inéditas..."):
                texto = extrair_texto_pdf(pdf_base)
                client = get_gemini_client(google_key)
                
                prompt = f"""
                Crie {qtd} questões nível {dif} baseadas no texto.
                JSON: [{{ 
                    "enunciado": "...", 
                    "alternativas": ["A)...", "B)..."], 
                    "resposta_correta": "...", 
                    "comentario_ia": {{ "comentario_geral": "...", "analise_alternativas": [], "fontes": "..." }} 
                }}]
                Texto: {texto[:100000]}
                """
                resp = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        response_mime_type='application/json'
                    )
                )
                novas_questoes = json.loads(resp.text)
                
                # Salvar em Lote no Supabase
                dados_para_banco = []
                for q in novas_questoes:
                    dados_para_banco.append({
                        "enunciado": q['enunciado'],
                        "alternativas": q['alternativas'],
                        "resposta_correta": q['resposta_correta'],
                        "comentario_ia": q['comentario_ia'],
                        "dificuldade": dif,
                        "fonte_original": "Gerado por IA"
                    })
                
                st.session_state.supabase.table("questoes").insert(dados_para_banco).execute()
                st.success(f"{len(novas_questoes)} questões geradas e salvas no Banco de Dados!")

# --- MODO 3: BANCO DE QUESTÕES (O QUE JÁ FOI SALVO) ---
elif modo == "📚 Banco de Questões Salvas":
    st.header("Meu Banco de Questões")
    
    if st.session_state.supabase:
        # Busca tudo o que já foi salvo
        response = st.session_state.supabase.table("questoes").select("*").execute()
        questoes_salvas = response.data
        
        st.metric("Total de Questões no Banco", len(questoes_salvas))
        
        q_sel = st.selectbox("Selecione para Revisar:", questoes_salvas, format_func=lambda x: f"{x['id']} - {x['enunciado'][:50]}...")
        
        if q_sel:
            st.write(q_sel['enunciado'])
            st.info(f"Gabarito: {q_sel['resposta_correta']}")
            
            # Recupera o comentário salvo sem gastar IA
            comentario = q_sel['comentario_ia']
            st.markdown("### Comentários (Carregado do Banco)")
            st.write(comentario.get('comentario_geral', ''))
            
            # Mostra detalhes se houver
            if 'analise_alternativas' in comentario:
                for item in comentario['analise_alternativas']:
                    st.write(f"- {item.get('status')}: {item.get('motivo')}")
            
    else:
        st.warning("Conecte o Supabase na barra lateral.")
