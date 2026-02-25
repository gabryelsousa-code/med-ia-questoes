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
    return hashlib.md5(enunciado.encode()).hexdigest()

def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)

# --- MENU LATERAL ---
with st.sidebar:
    st.title("🦉 MedBank AI")
    
    with st.expander("Configurar Acessos", expanded=True):
        google_key = st.text_input("Google API Key (AIza...):", type="password")
        supa_url = st.text_input("Supabase URL:", type="password")
        supa_key = st.text_input("Supabase Key:", type="password")
    
    if supa_url and supa_key:
        st.session_state.supabase = init_supabase(supa_url, supa_key)
        if st.session_state.supabase:
            st.success("Banco Conectado!")
        else:
            st.error("Erro na conexão Supabase")
    
    st.markdown("---")
    modo = st.radio("Menu:", ["📝 Resolver Questões", "⚡ Gerador de Questões", "📚 Banco Salvo"])

# --- MODO 1: RESOLVER QUESTÕES ---
if modo == "📝 Resolver Questões":
    st.header("Upload de Lista de Questões")
    arquivo = st.file_uploader("PDF da Prova", type="pdf")
    
    if arquivo and google_key:
        if 'questoes_extraidas' not in st.session_state:
            if st.button("🔍 Extrair Questões"):
                with st.spinner("Lendo PDF..."):
                    try:
                        texto = extrair_texto_pdf(arquivo)
                        client = get_gemini_client(google_key)
                        prompt = f"""
                        Extraia as questões. JSON: [{{ "enunciado": "...", "alternativas": ["A)..."] }}]
                        Texto: {texto[:100000]}
                        """
                        resp = client.models.generate_content(
                            model='gemini-flash-latest',
                            contents=prompt,
                            config=types.GenerateContentConfig(response_mime_type='application/json')
                        )
                        st.session_state.questoes_extraidas = json.loads(resp.text)
                        st.session_state.nome_arquivo_atual = arquivo.name
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao extrair: {e}")

    if 'questoes_extraidas' in st.session_state:
        qs = st.session_state.questoes_extraidas
        idx = st.selectbox("Questão:", range(len(qs)), format_func=lambda x: f"Questão {x+1}")
        q = qs[idx]
        
        st.write(q['enunciado'])
        resp_user = st.radio("Alternativas:", q['alternativas'], key=gerar_hash_questao(q['enunciado']))
        
        if st.button("Responder e Corrigir"):
            ja_existe = False
            # 1. Tenta buscar no banco
            if st.session_state.supabase:
                try:
                    res = st.session_state.supabase.table("questoes").select("*").eq("enunciado", q['enunciado']).execute()
                    if res.data:
                        st.session_state.correcao_atual = res.data[0]
                        ja_existe = True
                except:
                    pass
            
            # 2. Se não achou, gera com IA
            if not ja_existe:
                with st.spinner("Pesquisando..."):
                    try:
                        client = get_gemini_client(google_key)
                        prompt_corr = f"""
                        Corrija a questão usando Google Search (Estratégia MED/Diretrizes).
                        Questão: {q['enunciado']}
                        Alternativas: {q['alternativas']}
                        JSON: {{ "resposta_correta": "...", "comentario_geral": "...", "analise_alternativas": [{{ "alt": "A", "status": "...", "motivo": "..." }}], "fontes": "..." }}
                        """
                        resp = client.models.generate_content(
                            model='gemini-flash-latest',
                            contents=prompt_corr,
                            config=types.GenerateContentConfig(
                                tools=[types.Tool(google_search=types.GoogleSearch())],
                                response_mime_type='application/json'
                            )
                        )
                        dados_ia = json.loads(resp.text)
                        
                        # Salva no banco
                        if st.session_state.supabase:
                            novo = {
                                "enunciado": q['enunciado'],
                                "alternativas": q['alternativas'],
                                "resposta_correta": dados_ia['resposta_correta'],
                                "comentario_ia": dados_ia,
                                "fonte_original": st.session_state.get('nome_arquivo_atual', 'Upload')
                            }
                            st.session_state.supabase.table("questoes").insert(novo).execute()
                        
                        st.session_state.correcao_atual = {"comentario_ia": dados_ia}
                    except Exception as e:
                        st.error(f"Erro na correção: {e}")

        # Exibe Correção
        if 'correcao_atual' in st.session_state:
            c = st.session_state.correcao_atual.get('comentario_ia', {})
            st.markdown("---")
            st.success(f"Gabarito: {c.get('resposta_correta')}")
            st.info(c.get('comentario_geral'))
            for item in c.get('analise_alternativas', []):
                icon = "✅" if "correta" in item.get('status', '').lower() else "❌"
                st.write(f"{icon} {item.get('alt')}: {item.get('motivo')}")

# --- MODO 2: GERADOR ---
elif modo == "⚡ Gerador de Questões":
    st.header("Gerador de Simulados")
    pdf = st.file_uploader("Material Base", type="pdf")
    qtd = st.slider("Qtd", 1, 20, 5)
    dif = st.selectbox("Dificuldade", ["R1", "R3", "Título"])
    
    if pdf and st.button("Gerar") and google_key:
        with st.spinner("Gerando..."):
            try:
                texto = extrair_texto_pdf(pdf)
                client = get_gemini_client(google_key)
                prompt = f"""
                Crie {qtd} questões nível {dif}.
                JSON: [{{ "enunciado": "...", "alternativas": ["..."], "resposta_correta": "...", "comentario_ia": {{ "comentario_geral": "...", "analise_alternativas": [] }} }}]
                Texto: {texto[:100000]}
                """
                resp = client.models.generate_content(
                    model='gemini-flash-latest',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        response_mime_type='application/json'
                    )
                )
                novas = json.loads(resp.text)
                
                if st.session_state.supabase:
                    dados_banco = []
                    for n in novas:
                        dados_banco.append({
                            "enunciado": n['enunciado'],
                            "alternativas": n['alternativas'],
                            "resposta_correta": n['resposta_correta'],
                            "comentario_ia": n['comentario_ia'],
                            "dificuldade": dif,
                            "fonte_original": "Gerado IA"
                        })
                    st.session_state.supabase.table("questoes").insert(dados_banco).execute()
                    st.success("Salvo no banco!")
                else:
                    st.json(novas)
            except Exception as e:
                st.error(f"Erro: {e}")

# --- MODO 3: BANCO SALVO ---
elif modo == "📚 Banco Salvo":
    st.header("Questões Salvas")
    if st.session_state.supabase:
        try:
            res = st.session_state.supabase.table("questoes").select("*").execute()
            qs = res.data
            if qs:
                sel = st.selectbox("Revisar:", qs, format_func=lambda x: f"{x['id']} - {x['enunciado'][:60]}...")
                st.write(sel['enunciado'])
                st.success(f"Gabarito: {sel['resposta_correta']}")
                c = sel['comentario_ia']
                st.write(c.get('comentario_geral'))
            else:
                st.info("Banco vazio.")
        except Exception as e:
            st.error(f"Erro ao ler banco: {e}")
    else:
        st.warning("Conecte o Supabase.")
